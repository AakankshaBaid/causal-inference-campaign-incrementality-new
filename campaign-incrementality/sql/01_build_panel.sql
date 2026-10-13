-- =====================================================================
-- Campaign incrementality: building the measurement panel
-- =====================================================================
--
-- This is the contract between the warehouse and the Python package. The
-- estimator consumes ONE table shaped like `campaign_panel` below; everything
-- upstream is warehouse work, everything downstream is modelling. Only this
-- file is dialect-specific.
--
-- ANSI SQL with Trino-style date functions. Table names are generic
-- placeholders: swap in your own fact and dimension tables.
--
-- Grain: one row per (property_id, week), weeks keyed on Monday.
--
-- Design note -- what the estimate does and does not use
-- ------------------------------------------------------
-- The campaign runs in every market at once, so no untreated lodging series
-- is a valid control: every non-participating property sits beside discounted
-- competitors. The headline design therefore controls on
--   (a) NON-LODGING production (air, car, activities), which a lodging deal
--       cannot discount, and
--   (b) marketplace-wide demand signals (metasearch, paid search, destination
--       queries, site traffic).
-- Those are market-level series, joined by week in step 6.
--
-- Enrolled properties that dropped out (deal not live throughout) are removed from
-- EVERY cohort, and so are properties whose only competitor is such a partial
-- participant: all of them were exposed to the campaign, so none is a clean
-- "no campaign" unit.
--
-- Two untreated property groups ARE still built, for different jobs:
--   * `compset`    -- non-participants inside a participant's competitive set.
--                     The second causal model treats these as the
--                     intervention, to measure cannibalisation or halo.
--   * `distant`    -- non-participants outside every participant's competitive
--                     set. PLACEBO UNITS ONLY: they let the random-group test
--                     show what "no campaign" looks like. They are not a
--                     control, and any spillover onto them makes that test
--                     slightly conservative rather than invalidating it.
--
-- Parameters (pass from the orchestrator so SQL and YAML cannot disagree):
--   :campaign_name        the bulk-load identifier
--   :prior_campaign_name  last year's equivalent campaign
--   :activation_week      Monday of the week the deal went live
--   :pre_weeks            78
--   :post_weeks           8
-- =====================================================================


-- ---------------------------------------------------------------------
-- 1. Participating properties, with dropout screening
-- ---------------------------------------------------------------------
-- A property that switched the deal off in week 3 is not a treated unit for
-- weeks 3-8. Leaving partial participants in attenuates the estimate toward
-- zero, invisibly, so the screen happens here rather than being noticed later.
CREATE OR REPLACE VIEW campaign_treated_properties AS
WITH enrolled AS (
    SELECT DISTINCT
        bl.property_id,
        bl.rate_rule_id
    FROM promo_bulk_load_scope AS bl
    JOIN property_attributes AS pa
      ON pa.property_id = bl.property_id
    WHERE bl.bulk_load_type = :campaign_name
      AND pa.property_category = 'Hotel'
      AND pa.is_test_property = FALSE
),
live AS (
    SELECT
        e.property_id,
        COUNT(DISTINCT da.snapshot_date)                  AS live_days,
        MIN(CASE WHEN da.is_promo_live THEN 1 ELSE 0 END) AS live_throughout
    FROM enrolled AS e
    LEFT JOIN deal_attributes_daily AS da
      ON da.rate_rule_id = e.rate_rule_id
     AND da.snapshot_date >= DATE_ADD('week', 1, :activation_week)
     AND da.snapshot_date <  DATE_ADD('week', :post_weeks, :activation_week)
    GROUP BY 1
)
SELECT property_id
FROM live
WHERE live_throughout = 1
  AND live_days = 7 * (:post_weeks - 1);          -- full post window, no gaps


-- ---------------------------------------------------------------------
-- 2. Repeat participation
-- ---------------------------------------------------------------------
-- With high repeat participation the pre-period contains LAST year's campaign.
-- The model needs to know, because otherwise it absorbs that episode as
-- seasonality and understates this year's effect (worth ~3 points of bias in
-- simulation).
CREATE OR REPLACE VIEW campaign_repeat_participants AS
SELECT DISTINCT bl.property_id
FROM promo_bulk_load_scope AS bl
WHERE bl.bulk_load_type = :prior_campaign_name
  AND bl.property_id IN (SELECT property_id FROM campaign_treated_properties);


-- ---------------------------------------------------------------------
-- 2b. Everyone who enrolled, including dropouts
-- ---------------------------------------------------------------------
-- A dropout is not a treated unit, but it is not an untreated one either. This
-- view exists so the untreated groups below can exclude it. An earlier version
-- tested only against the screened treated list, which let partial
-- participants fall into the untreated placebo group.
CREATE OR REPLACE VIEW campaign_enrolled_properties AS
SELECT DISTINCT bl.property_id
FROM promo_bulk_load_scope AS bl
WHERE bl.bulk_load_type = :campaign_name;


-- ---------------------------------------------------------------------
-- 3. Competitive set: the SECOND causal model's treatment group
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW campaign_compset_properties AS
WITH compset_map AS (
    SELECT DISTINCT
        c.property_id,
        CONCAT(CAST(c.market_id AS VARCHAR), '-', CAST(c.compset_id AS VARCHAR)) AS compset_key
    FROM property_compset AS c
    JOIN property_attributes AS pa
      ON pa.property_id = c.property_id
    WHERE c.snapshot_date = (SELECT MAX(snapshot_date) FROM property_compset)
      AND pa.property_category = 'Hotel'
),
treated_keys AS (
    SELECT DISTINCT m.compset_key
    FROM compset_map AS m
    JOIN campaign_treated_properties AS t
      ON t.property_id = m.property_id
)
SELECT DISTINCT m.property_id
FROM compset_map AS m
JOIN treated_keys AS k
  ON k.compset_key = m.compset_key
WHERE m.property_id NOT IN (SELECT property_id FROM campaign_enrolled_properties);


-- ---------------------------------------------------------------------
-- 4. Other non-participants: placebo units, NOT a control
-- ---------------------------------------------------------------------
CREATE OR REPLACE VIEW campaign_other_properties AS
WITH enrolled_sets AS (
    SELECT DISTINCT CONCAT(CAST(c.market_id AS VARCHAR), '-', CAST(c.compset_id AS VARCHAR)) AS compset_key
    FROM property_compset AS c
    WHERE c.snapshot_date = (SELECT MAX(snapshot_date) FROM property_compset)
      AND c.property_id IN (SELECT property_id FROM campaign_enrolled_properties)
),
exposed AS (
    -- anyone sharing a competitive set with ANY enrolled property
    SELECT DISTINCT c.property_id
    FROM property_compset AS c
    WHERE c.snapshot_date = (SELECT MAX(snapshot_date) FROM property_compset)
      AND CONCAT(CAST(c.market_id AS VARCHAR), '-', CAST(c.compset_id AS VARCHAR))
          IN (SELECT compset_key FROM enrolled_sets)
)
SELECT pa.property_id
FROM property_attributes AS pa
WHERE pa.property_category = 'Hotel'
  AND pa.is_test_property = FALSE
  AND pa.property_id NOT IN (SELECT property_id FROM campaign_enrolled_properties)
  AND pa.property_id NOT IN (SELECT property_id FROM exposed);


-- ---------------------------------------------------------------------
-- 5. Weekly property production and traffic
-- ---------------------------------------------------------------------
-- Net of cancellations at campaign close, so the outcome is what was kept.
CREATE OR REPLACE VIEW campaign_weekly_production AS
SELECT
    t.property_id,
    DATE_TRUNC('week', t.transaction_date)   AS week,
    SUM(t.gross_booking_value_usd)           AS gbv,
    SUM(t.room_night_count)                  AS room_nights,
    COUNT(DISTINCT t.booking_item_id)        AS bookings
FROM booking_transactions AS t
WHERE t.transaction_date >= DATE_ADD('week', -(:pre_weeks + 105), :activation_week)
  AND t.transaction_date <  DATE_ADD('week',   :post_weeks,       :activation_week)
  AND t.cancellation_flag = FALSE
GROUP BY 1, 2;

CREATE OR REPLACE VIEW campaign_weekly_traffic AS
SELECT
    v.property_id,
    DATE_TRUNC('week', v.visit_date) AS week,
    SUM(v.visit_count)               AS visits
FROM property_traffic_daily AS v
WHERE v.visit_date >= DATE_ADD('week', -(:pre_weeks + 105), :activation_week)
  AND v.visit_date <  DATE_ADD('week',   :post_weeks,       :activation_week)
GROUP BY 1, 2;


-- ---------------------------------------------------------------------
-- 6. Market-level controls (the predictors the headline design uses)
-- ---------------------------------------------------------------------
-- Non-lodging production: air, car, activities. Global, weekly.
-- Residual exposure is cross-sell -- a traveller taking the hotel deal may
-- attach a car -- which makes the estimate mildly conservative.
CREATE OR REPLACE VIEW campaign_weekly_market_controls AS
WITH other_products AS (
    SELECT
        DATE_TRUNC('week', o.transaction_date) AS week,
        SUM(o.gross_booking_value_usd)         AS other_products_volume
    FROM booking_transactions_non_lodging AS o
    WHERE o.cancellation_flag = FALSE
    GROUP BY 1
),
demand AS (
    SELECT
        DATE_TRUNC('week', d.demand_date) AS week,
        SUM(d.metasearch_impressions)     AS meta_impressions,
        SUM(d.destination_query_count)    AS destination_queries,
        SUM(d.site_visitor_count)         AS market_visitors,
        SUM(d.site_purchase_count)        AS market_purchases
    FROM market_demand_daily AS d
    GROUP BY 1
),
search AS (
    SELECT
        DATE_TRUNC('week', s.click_date) AS week,
        SUM(s.click_count)               AS search_clicks
    FROM paid_search_daily AS s
    GROUP BY 1
)
SELECT
    demand.week,
    op.other_products_volume,
    demand.meta_impressions,
    demand.destination_queries,
    demand.market_visitors,
    demand.market_purchases,
    search.search_clicks
FROM demand
LEFT JOIN other_products AS op ON op.week = demand.week
LEFT JOIN search               ON search.week = demand.week;


-- ---------------------------------------------------------------------
-- 7. Assemble the panel
-- ---------------------------------------------------------------------
CREATE OR REPLACE TABLE campaign_panel AS
WITH cohorts AS (
    SELECT property_id, 'treated' AS cohort FROM campaign_treated_properties
    UNION ALL
    SELECT property_id, 'compset' AS cohort FROM campaign_compset_properties
    UNION ALL
    SELECT property_id, 'distant' AS cohort FROM campaign_other_properties
),
base AS (
    SELECT
        p.property_id,
        p.week,
        c.cohort,
        p.gbv,
        p.room_nights,
        p.bookings,
        tr.visits,
        YEAR_OF_WEEK(p.week) AS iso_year,
        WEEK_OF_YEAR(p.week) AS iso_week
    FROM campaign_weekly_production AS p
    JOIN cohorts AS c
      ON c.property_id = p.property_id
    LEFT JOIN campaign_weekly_traffic AS tr
      ON tr.property_id = p.property_id AND tr.week = p.week
),
with_ly AS (
    -- Same property, same ISO week, previous ISO year. Joined on
    -- (iso_year, iso_week) rather than `week - 52 weeks`: for Monday-keyed
    -- weeks the two usually agree, but they diverge around 53-week ISO years
    -- (2020, 2026), sliding the comparison by a week -- harmless in June,
    -- material in late December. ISO week 53 has no prior-year counterpart
    -- and correctly returns NULL rather than silently matching week 52.
    SELECT b.*, ly.gbv AS outcome_ly
    FROM base AS b
    LEFT JOIN base AS ly
      ON  ly.property_id = b.property_id
      AND ly.iso_year    = b.iso_year - 1
      AND ly.iso_week    = b.iso_week
)
SELECT
    w.property_id,
    w.week,
    w.cohort,
    COALESCE(s.allows_stacking, FALSE)                   AS stack_eligible,
    CASE WHEN r.property_id IS NOT NULL THEN 1 ELSE 0 END AS repeat_participant,
    w.gbv,
    w.room_nights,
    w.bookings,
    w.visits,
    w.outcome_ly,
    mc.other_products_volume,
    mc.meta_impressions,
    mc.destination_queries,
    mc.market_visitors,
    mc.market_purchases,
    mc.search_clicks
FROM with_ly AS w
LEFT JOIN campaign_weekly_market_controls AS mc ON mc.week = w.week
LEFT JOIN property_stacking_config        AS s  ON s.property_id = w.property_id
LEFT JOIN campaign_repeat_participants    AS r  ON r.property_id = w.property_id
WHERE w.week >= DATE_ADD('week', -(:pre_weeks + 52), :activation_week);


-- ---------------------------------------------------------------------
-- 8. Pre-flight checks -- run BEFORE the estimator
-- ---------------------------------------------------------------------
-- Each corresponds to a failure that yields a plausible-looking but wrong
-- number rather than an error.
SELECT
    cohort,
    COUNT(DISTINCT week)                                                AS weeks,
    COUNT(DISTINCT property_id)                                         AS properties,
    SUM(CASE WHEN gbv <= 0 THEN 1 ELSE 0 END)                           AS non_positive_gbv,
    SUM(CASE WHEN other_products_volume IS NULL THEN 1 ELSE 0 END)      AS null_cross_product,
    SUM(CASE WHEN search_clicks IS NULL THEN 1 ELSE 0 END)              AS null_search_clicks,
    SUM(CASE WHEN visits IS NULL THEN 1 ELSE 0 END)                     AS null_visits
FROM campaign_panel
GROUP BY 1
ORDER BY 1;

-- Cohort sizes must be stable week to week. A cohort that grows mid-window
-- means the enrolment screen leaked, and the level shift reads as effect.
SELECT cohort, week, COUNT(DISTINCT property_id) AS properties
FROM campaign_panel
GROUP BY 1, 2
ORDER BY 1, 2;

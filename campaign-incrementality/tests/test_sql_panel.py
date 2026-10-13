"""Execute the warehouse SQL against synthetic tables.

Parsing proves the SQL is well formed; it cannot prove the cohort logic is
right. This builds small source tables with known properties -- including one
deliberate dropout -- transpiles the Trino SQL to DuckDB, runs the whole script
and asserts what comes out. It found a real defect: a hotel that ran the deal
for only part of the window was landing in the untreated placebo group.

Skipped when the optional dependencies are not installed.
"""

from __future__ import annotations

import datetime as dt
import re
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

duckdb = pytest.importorskip("duckdb")
sqlglot = pytest.importorskip("sqlglot")
warnings.filterwarnings("ignore")

SQL_PATH = Path(__file__).resolve().parents[1] / "sql" / "01_build_panel.sql"


def run(sql_path):
    con = duckdb.connect()
    rng = np.random.default_rng(0)
    act = dt.date(2025, 6, 30)
    start = act - dt.timedelta(weeks=78 + 105 + 3)
    end = act + dt.timedelta(weeks=9)
    days = pd.date_range(start, end, freq="D")
    P = list(range(1, 61))
    T, C, OTHER = P[:20], P[20:40], P[40:]

    def put(name, df):
        con.register("_t", df)
        con.execute(f"create table {name} as select * from _t")
        con.unregister("_t")

    put(
        "property_attributes",
        pd.DataFrame({"property_id": P, "property_category": "Hotel", "is_test_property": False}),
    )
    put(
        "promo_bulk_load_scope",
        pd.concat(
            [
                pd.DataFrame(
                    {"property_id": T, "rate_rule_id": [1000 + p for p in T], "bulk_load_type": "c"}
                ),
                pd.DataFrame(
                    {
                        "property_id": T[:15],
                        "rate_rule_id": [2000 + p for p in T[:15]],
                        "bulk_load_type": "p",
                    }
                ),
            ]
        ),
    )
    live_days = pd.date_range(
        act + dt.timedelta(weeks=1), act + dt.timedelta(weeks=8) - dt.timedelta(days=1), freq="D"
    )
    rows = [
        (1000 + p, d.date(), not (p == 20 and d.date() == (act + dt.timedelta(weeks=3))))
        for p in T
        for d in live_days
    ]  # property 20 drops out in week 3
    put(
        "deal_attributes_daily",
        pd.DataFrame(rows, columns=["rate_rule_id", "snapshot_date", "is_promo_live"]),
    )
    comp = {**{p: p for p in T}, **{p: p - 20 for p in C}, **{p: 100 + p for p in OTHER}}
    put(
        "property_compset",
        pd.DataFrame(
            {
                "property_id": P,
                "market_id": 1,
                "compset_id": [comp[p] for p in P],
                "snapshot_date": act,
            }
        ),
    )
    n = len(P) * len(days)
    pid = np.repeat(P, len(days))
    dts = np.tile(days.date, len(P))
    put(
        "booking_transactions",
        pd.DataFrame(
            {
                "property_id": pid,
                "transaction_date": dts,
                "gross_booking_value_usd": rng.lognormal(7, 0.4, n),
                "room_night_count": rng.integers(1, 6, n),
                "booking_item_id": np.arange(n),
                "cancellation_flag": rng.random(n) < 0.08,
            }
        ),
    )
    put(
        "property_traffic_daily",
        pd.DataFrame(
            {"property_id": pid, "visit_date": dts, "visit_count": rng.integers(50, 400, n)}
        ),
    )
    d = len(days)
    put(
        "booking_transactions_non_lodging",
        pd.DataFrame(
            {
                "transaction_date": days.date,
                "gross_booking_value_usd": rng.lognormal(12, 0.2, d),
                "cancellation_flag": False,
            }
        ),
    )
    put(
        "market_demand_daily",
        pd.DataFrame(
            {
                "demand_date": days.date,
                "metasearch_impressions": rng.integers(1e5, 2e5, d),
                "destination_query_count": rng.integers(1e4, 2e4, d),
                "site_visitor_count": rng.integers(1e5, 2e5, d),
                "site_purchase_count": rng.integers(1e3, 2e3, d),
            }
        ),
    )
    put(
        "paid_search_daily",
        pd.DataFrame({"click_date": days.date, "click_count": rng.integers(1e4, 3e4, d)}),
    )
    put(
        "property_stacking_config",
        pd.DataFrame({"property_id": T, "allows_stacking": rng.random(len(T)) < 0.5}),
    )
    txt = Path(sql_path).read_text()
    sub = {
        "campaign_name": "'c'",
        "prior_campaign_name": "'p'",
        "activation_week": "DATE '2025-06-30'",
        "pre_weeks": "78",
        "post_weeks": "8",
    }
    txt = re.sub(r"(?<![\w:]):([a-z_]+)\b", lambda m: sub[m.group(1)], txt)
    out = []
    for i, stmt in enumerate(sqlglot.transpile(txt, read="trino", write="duckdb")):
        try:
            r = con.execute(stmt)
            if stmt.lstrip().upper().startswith("SELECT"):
                out.append(r.fetchdf())
        except Exception as e:
            return {"error": f"statement {i}: {str(e)[:260]}", "sql": stmt[:240]}
    panel = con.execute("select * from campaign_panel").fetchdf()
    panel["week"] = pd.to_datetime(panel["week"])
    sizes = panel.groupby("cohort").property_id.nunique().to_dict()
    res = {
        "columns_ok": {
            "property_id",
            "week",
            "cohort",
            "stack_eligible",
            "repeat_participant",
            "gbv",
            "room_nights",
            "bookings",
            "visits",
            "outcome_ly",
            "other_products_volume",
            "meta_impressions",
            "destination_queries",
            "market_visitors",
            "market_purchases",
            "search_clicks",
        }
        <= set(panel.columns),
        "cohort_sizes": sizes,
        "dropout_in_panel": bool((panel.property_id == 20).any()),
        "dropout_cohort": panel.loc[panel.property_id == 20, "cohort"].unique().tolist(),
        "peer_of_dropout_in_panel": bool((panel.property_id == 40).any()),
        "repeat_participants": int(
            panel[panel.cohort == "treated"].groupby("property_id").repeat_participant.first().sum()
        ),
        "weeks_all_mondays": bool((panel.week.dt.dayofweek == 0).all()),
        "weeks_range": (str(panel.week.min().date()), str(panel.week.max().date())),
        "nulls_in_window": {
            c: int(panel[panel.week >= "2024-07-01"][c].isna().sum())
            for c in [
                "gbv",
                "visits",
                "outcome_ly",
                "other_products_volume",
                "search_clicks",
                "meta_impressions",
            ]
        },
    }
    # prior-year join: same property, same ISO week, previous ISO year
    p1 = panel[(panel.property_id == 1)].set_index("week")
    w = pd.Timestamp("2025-03-03")
    ly = p1.loc[w - pd.Timedelta(weeks=52), "gbv"]
    res["outcome_ly_matches_prior_year"] = bool(np.isclose(p1.loc[w, "outcome_ly"], ly))
    res["preflight_rows"] = [len(x) for x in out]
    return res


@pytest.fixture(scope="module")
def result():
    return run(SQL_PATH)


def test_sql_runs_end_to_end(result):
    assert "error" not in result, result.get("error")
    assert result["columns_ok"], "panel is missing a column the estimator reads"
    assert result["weeks_all_mondays"]
    assert all(v == 0 for v in result["nulls_in_window"].values()), result["nulls_in_window"]


def test_prior_year_join_matches_the_same_iso_week(result):
    assert result["outcome_ly_matches_prior_year"]


def test_dropout_is_excluded_from_every_cohort(result):
    """Property 20 enrolled but dropped out in week 3; property 40's only
    competitor is property 20. Neither is a clean treated or untreated unit."""
    assert not result["dropout_in_panel"], f"dropout landed in {result['dropout_cohort']}"
    assert not result["peer_of_dropout_in_panel"]


def test_cohort_sizes_follow_the_rules(result):
    assert result["cohort_sizes"] == {"treated": 19, "compset": 19, "distant": 20}
    assert result["repeat_participants"] == 15

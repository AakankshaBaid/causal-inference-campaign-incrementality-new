# Decision memo: Mid Year Sale 2025

_Generated from pipeline run. Activation week 2025-06-30; measurement window 2025-07-07 to 2025-08-04 (5 weeks)._

## Headline

Net incrementality: **+6.4%** on GBV (90% interval +3.0% to +10.0%), worth **$25.9M**. Verdict: material effect.

| Build | Rate | Value |
| --- | ---: | ---: |
| Participating properties | +9.5% | $38.3M |
| Less cannibalisation of competitive set | -2.7% | -$12.4M |
| Total incrementality | +6.4% | $25.9M |

Room nights moved +12.5% against booking value's +9.5%; the gap is the discount reaching travellers.

## Drivers of growth

The GBV lift is carried by conversion rate at +8.7% and traffic (visits) at +2.4%, partly given back through average daily rate at -2.7%.

| Driver | Lift | 90% interval | Share of movement |
| --- | ---: | ---: | ---: |
| Traffic (visits) | +2.4% | +0.3% to +4.4% | 16% |
| Conversion rate | +8.7% | +7.9% to +9.4% | 57% |
| Length of stay | +1.1% | +0.8% to +1.3% | 8% |
| Average daily rate | -2.7% | -2.9% to -2.6% | 19% |

Drivers compose to +9.45% against a directly estimated +9.53% — a residual of +0.08%, which reconciles.

## Money

| Line | USD |
| --- | --- |
| Incremental booking value | $25.88M |
| Incremental contribution | $3.24M |
| Cash-funded discount | -$1.33M |
| Fixed campaign cost | -$0.70M |
| Net value | $1.20M |

Return on campaign spend: **1.59x** (net $1.2M). Break-even lift: **4.0%**, against a measured total of 6.4%. Of the $14.8M discount granted, **$12.2M (83%)** went to demand the model says would have converted anyway.

The 90% interval +3.0% to +10.0% spans break-even (4.0%), so this readout cannot say whether the campaign paid back. In money terms the same range runs from -$0.5M to $3.0M on a $2.0M bill (0.75x to 2.46x).

## What the displacement test is worth

| | Gross of displacement | Net of displacement |
| --- | --- | --- |
| Incremental booking value | $38.3M | $25.9M |
| Effective lift | 9.5% | 6.4% |
| Return on spend | 2.36x | 1.59x |
| Net value | $2.75M | $1.20M |

Both readings fall on the same side of break-even, so the displacement adjustment changes the size of the answer but not the decision.

## Falsification scorecard

| Test | Result | Statistic | Detail |
| --- | --- | --- | --- |
| Rolling-origin backtest | PASS | 0.0194 | 22 origins, 5-week horizon, mean absolute error 1.94% |
| In-time placebo | PASS | 0.0187 | fake activation 2025-04-07 (12 weeks early) returns +1.87% |
| In-space placebo | PASS | 0.0588 | 16 untreated cohorts of 1000 properties; null sd 0.44%; observed +9.53% ranks 1/17 |
| Comp-set displacement | PASS | -0.0267 | untreated comp set moves -2.67% over the same weeks; netted off the headline as displacement |
| Control-pool leakage (underpowered) | PASS | -0.0021 | control pool reads -0.2% against unaffected demand, detectable only to +/-1.5% -- rules out gross contamination, cannot confirm the 1-2% that would matter; design does not use the pool as a control |
| Relationship stability | PASS | 0.0194 | forecast error 1.00x from older to recent origins (1.94% to 1.94%); early vs late pre-period counterfactuals diverge 1.94% |
| Specification sensitivity | PASS | 0.0120 | 6 comparable alternatives span +8.98% to +10.19% (1.20% wide); 3 that forecast worse are reported but not counted |

## Stacking

Stack-enabled properties outperformed stack-disabled participants by **+2.3%** (90% CI +1.6% to +3.1%, p=0.000). Parallel-trends check p=0.12 (holds).

## What this does not answer

- Post-window carryover: the measurement stops at the campaign end date, so any repeat-booking effect is excluded and the estimate is a lower bound.
- Participation is not randomised. Properties opted into the campaign, so the estimate is the effect on participants, not the effect of extending the campaign to non-participants.
- The discount-depth ceiling holds volume fixed; a shallower discount would presumably have produced less lift.

# Decision memo: Spring Sale 2025

_Generated from pipeline run. Activation week 2025-03-31; measurement window 2025-04-07 to 2025-05-05 (5 weeks)._

## Headline

Net incrementality: **+5.9%** on GBV (90% interval +2.8% to +8.8%), worth **$21.4M**. Verdict: material effect.

| Build | Rate | Value |
| --- | ---: | ---: |
| Participating properties | +9.3% | $33.7M |
| Less cannibalisation of competitive set | -2.9% | -$12.3M |
| Total incrementality | +5.9% | $21.4M |

Room nights moved +12.5% against booking value's +9.3%; the gap is the discount reaching travellers.

## Drivers of growth

The GBV lift is carried by conversion rate at +8.6% and traffic (visits) at +2.5%, partly given back through average daily rate at -2.9%.

| Driver | Lift | 90% interval | Share of movement |
| --- | ---: | ---: | ---: |
| Traffic (visits) | +2.5% | +0.8% to +4.3% | 16% |
| Conversion rate | +8.6% | +7.6% to +9.2% | 56% |
| Length of stay | +1.1% | +0.8% to +1.5% | 7% |
| Average daily rate | -2.9% | -3.2% to -2.7% | 20% |

Drivers compose to +9.21% against a directly estimated +9.31% — a residual of +0.09%, which reconciles.

## Money

| Line | USD |
| --- | --- |
| Incremental booking value | $21.44M |
| Incremental contribution | $2.68M |
| Cash-funded discount | -$0.85M |
| Fixed campaign cost | -$0.45M |
| Net value | $1.38M |

Return on campaign spend: **2.06x** (net $1.4M). Break-even lift: **2.9%**, against a measured total of 5.9%. Of the $10.7M discount granted, **$8.8M (83%)** went to demand the model says would have converted anyway.

The 90% interval +2.8% to +8.8% spans break-even (2.9%), so this readout cannot say whether the campaign paid back. In money terms the same range runs from -$0.04M to $2.7M on a $1.3M bill (0.97x to 3.06x).

## What the displacement test is worth

| | Gross of displacement | Net of displacement |
| --- | --- | --- |
| Incremental booking value | $33.7M | $21.4M |
| Effective lift | 9.3% | 5.9% |
| Return on spend | 3.23x | 2.06x |
| Net value | $2.91M | $1.38M |

Both readings fall on the same side of break-even, so the displacement adjustment changes the size of the answer but not the decision.

## Falsification scorecard

| Test | Result | Statistic | Detail |
| --- | --- | --- | --- |
| Rolling-origin backtest | PASS | 0.0199 | 22 origins, 5-week horizon, mean absolute error 1.99% |
| In-time placebo | PASS | 0.0070 | fake activation 2024-09-30 (26 weeks early) returns +0.70% |
| In-space placebo | PASS | 0.0588 | 16 untreated cohorts of 1000 properties; null sd 0.50%; observed +9.31% ranks 1/17 |
| Comp-set displacement | PASS | -0.0294 | untreated comp set moves -2.94% over the same weeks; netted off the headline as displacement |
| Control-pool leakage (underpowered) | PASS | -0.0071 | control pool reads -0.7% against unaffected demand, detectable only to +/-1.5% -- rules out gross contamination, cannot confirm the 1-2% that would matter; design does not use the pool as a control |
| Relationship stability | PASS | 0.0189 | forecast error 1.04x from older to recent origins (1.96% to 2.03%); early vs late pre-period counterfactuals diverge 1.89% |
| Specification sensitivity | FAIL | 0.0348 | 7 comparable alternatives span +8.00% to +11.47% (3.48% wide); 2 that forecast worse are reported but not counted |

## Stacking

Stack-enabled properties outperformed stack-disabled participants by **+2.3%** (90% CI +1.6% to +3.1%, p=0.000). Parallel-trends check p=0.11 (holds).

## What this does not answer

- Post-window carryover: the measurement stops at the campaign end date, so any repeat-booking effect is excluded and the estimate is a lower bound.
- Participation is not randomised. Properties opted into the campaign, so the estimate is the effect on participants, not the effect of extending the campaign to non-participants.
- The discount-depth ceiling holds volume fixed; a shallower discount would presumably have produced less lift.

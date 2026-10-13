# Decision memo: Black Friday Campaign

_Generated from pipeline run. Activation week 2024-11-25; measurement window 2024-12-02 to 2025-01-13 (7 weeks)._

## Headline

Net incrementality: **+8.1%** on GBV (90% interval +5.2% to +11.9%), worth **$29.7M**. Verdict: material effect.

| Build | Rate | Value |
| --- | ---: | ---: |
| Participating properties | +10.5% | $38.3M |
| Less cannibalisation of competitive set | -2.1% | -$8.6M |
| Total incrementality | +8.1% | $29.7M |

Room nights moved +13.3% against booking value's +10.5%; the gap is the discount reaching travellers.

## Drivers of growth

The GBV lift is carried by conversion rate at +8.4% and traffic (visits) at +3.7%, partly given back through average daily rate at -2.4%.

| Driver | Lift | 90% interval | Share of movement |
| --- | ---: | ---: | ---: |
| Traffic (visits) | +3.7% | +1.6% to +6.5% | 24% |
| Conversion rate | +8.4% | +7.8% to +9.3% | 54% |
| Length of stay | +0.9% | +0.8% to +1.1% | 6% |
| Average daily rate | -2.4% | -2.7% to -2.1% | 16% |

Drivers compose to +10.74% against a directly estimated +10.52% — a residual of -0.22%, which reconciles.

## Money

| Line | USD |
| --- | --- |
| Incremental booking value | $29.69M |
| Incremental contribution | $3.71M |
| Cash-funded discount | -$2.31M |
| Fixed campaign cost | -$1.20M |
| Net value | $0.20M |

Return on campaign spend: **1.06x** (net $0.2M). Break-even lift: **7.7%**, against a measured total of 8.1%. Of the $23.1M discount granted, **$19.0M (82%)** went to demand the model says would have converted anyway.

The 90% interval +5.2% to +11.9% spans break-even (7.7%), so this readout cannot say whether the campaign paid back. In money terms the same range runs from -$1.2M to $1.9M on a $3.5M bill (0.67x to 1.54x).

## What the displacement test is worth

| | Gross of displacement | Net of displacement |
| --- | --- | --- |
| Incremental booking value | $38.3M | $29.7M |
| Effective lift | 10.5% | 8.1% |
| Return on spend | 1.37x | 1.06x |
| Net value | $1.28M | $0.20M |

Both readings fall on the same side of break-even, so the displacement adjustment changes the size of the answer but not the decision.

## Falsification scorecard

| Test | Result | Statistic | Detail |
| --- | --- | --- | --- |
| Rolling-origin backtest | PASS | 0.0206 | 20 origins, 7-week horizon, mean absolute error 2.06% |
| In-time placebo | PASS | 0.0076 | fake activation 2024-09-02 (12 weeks early) returns +0.76% |
| In-space placebo | PASS | 0.0588 | 16 untreated cohorts of 1000 properties; null sd 0.51%; observed +10.52% ranks 1/17 |
| Comp-set displacement | PASS | -0.0210 | untreated comp set moves -2.10% over the same weeks; netted off the headline as displacement |
| Control-pool leakage (underpowered) | PASS | 0.0005 | control pool reads +0.0% against unaffected demand, detectable only to +/-1.7% -- rules out gross contamination, cannot confirm the 1-2% that would matter; design does not use the pool as a control |
| Relationship stability | PASS | 0.0300 | forecast error 0.74x from older to recent origins (2.36% to 1.75%); early vs late pre-period counterfactuals diverge 3.00% |
| Specification sensitivity | FAIL | 0.0359 | 7 comparable alternatives span +8.38% to +11.97% (3.59% wide); 2 that forecast worse are reported but not counted |

## Stacking

Stack-enabled properties outperformed stack-disabled participants by **+2.1%** (90% CI +1.5% to +2.8%, p=0.000). Parallel-trends check p=0.72 (holds).

## What this does not answer

- Post-window carryover: the measurement stops at the campaign end date, so any repeat-booking effect is excluded and the estimate is a lower bound.
- Participation is not randomised. Properties opted into the campaign, so the estimate is the effect on participants, not the effect of extending the campaign to non-participants.
- The discount-depth ceiling holds volume fixed; a shallower discount would presumably have produced less lift.

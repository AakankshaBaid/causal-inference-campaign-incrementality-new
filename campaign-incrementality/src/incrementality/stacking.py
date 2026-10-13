"""Incremental value of logged-in discount stacking, via difference-in-differences.

Stacking is an extra discount shown only to signed-in members. Every
participating property gets the base campaign deal; only some allow stacking
on top. That contract split is the natural experiment: compare the campaign
uplift of stack-enabled properties against stack-disabled ones, and the
difference is the marginal value of stacking.

This is a cleaner identification problem than the campaign question itself --
both groups are treated, both face the same market, so the market-wide
confounders that force us into a counterfactual model above difference out.
What it is not is randomised: properties choose whether to allow stacking,
and the ones that do may differ systematically. Two defences below:

* a parallel-trends check on the pre-period, which is the assumption the
  design rests on and the first thing a reviewer should attack,
* CUPED-style adjustment using each property's own pre-period level, which
  strips out the between-property variance that has nothing to do with the
  treatment and typically halves the standard error.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from scipy import stats

from .config import CohortConfig


@dataclass
class StackingResult:
    n_stack: int
    n_no_stack: int
    stack_uplift: float
    no_stack_uplift: float
    incremental_stacking_value: float
    ci: tuple[float, float]
    p_value: float
    parallel_trends_p: float
    variance_reduction: float

    @property
    def parallel_trends_holds(self) -> bool:
        return self.parallel_trends_p > 0.10

    def summary_row(self) -> dict[str, object]:
        return {
            "stack_enabled_properties": self.n_stack,
            "stack_disabled_properties": self.n_no_stack,
            "stack_enabled_uplift": self.stack_uplift,
            "stack_disabled_uplift": self.no_stack_uplift,
            "stacking_marginal_value": self.incremental_stacking_value,
            "ci_low": self.ci[0],
            "ci_high": self.ci[1],
            "p_value": self.p_value,
            "parallel_trends_p": self.parallel_trends_p,
            "cuped_variance_reduction": self.variance_reduction,
        }


def _window_means(treated: pd.DataFrame, start, end, outcome: str) -> pd.Series:
    chunk = treated[(treated["week"] >= start) & (treated["week"] <= end)]
    return chunk.groupby("property_id")[outcome].mean()


def _property_window_means(panel: pd.DataFrame, cfg: CohortConfig, outcome: str) -> pd.DataFrame:
    """Per-property mean outcome in three equal-length windows.

    * ``post``     the campaign measurement window.
    * ``ref``      the weeks immediately BEFORE activation, same length.
    * ``pre_ref``  the equal-length block before that, used only to test the
                   parallel-trends assumption.

    The reference is deliberately not "the same calendar weeks last year". With
    high repeat participation those weeks contain LAST year's campaign, and for
    stack-enabled properties last year's stacking bonus too, so a reference
    built from them differs between the two groups for reasons unrelated to
    this year's stacking. Measured on 10 simulated campaigns, that reference
    made the parallel-trends check fail in 9 of 10 even though both groups
    were parallel by construction. Seasonality needs no adjustment here: both
    groups face the same calendar, so it cancels in the group difference.
    """
    treated = panel[panel["cohort"] == "treated"].copy()
    treated["week"] = pd.to_datetime(treated["week"])

    k = cfg.n_post_weeks
    activation = cfg.activation_week
    ref = (activation - pd.Timedelta(weeks=k), activation - pd.Timedelta(weeks=1))
    pre_ref = (
        activation - pd.Timedelta(weeks=2 * k),
        activation - pd.Timedelta(weeks=k + 1),
    )
    if treated["week"].min() > pre_ref[0]:
        raise ValueError(
            f"panel starts {treated['week'].min().date()}, but the stacking design "
            f"needs data from {pre_ref[0].date()}"
        )

    frame = pd.concat(
        [
            _window_means(treated, cfg.post_start, cfg.post_end, outcome).rename("post_mean"),
            _window_means(treated, *ref, outcome).rename("ref_mean"),
            _window_means(treated, *pre_ref, outcome).rename("pre_ref_mean"),
        ],
        axis=1,
    ).dropna()
    frame = frame[(frame > 0).all(axis=1)]
    eligible = treated.groupby("property_id")["stack_eligible"].first()
    frame["stack_eligible"] = eligible.reindex(frame.index).astype(int)
    frame["growth"] = np.log(frame["post_mean"] / frame["ref_mean"])
    frame["pre_growth"] = np.log(frame["ref_mean"] / frame["pre_ref_mean"])
    return frame


def estimate_stacking_value(
    panel: pd.DataFrame, cfg: CohortConfig, outcome: str | None = None
) -> StackingResult:
    """Difference-in-differences estimate of the marginal value of stacking."""
    outcome = outcome or cfg.primary_outcome
    frame = _property_window_means(panel, cfg, outcome)
    if frame["stack_eligible"].nunique() < 2:
        raise ValueError("need both stack-enabled and stack-disabled properties")

    stack = frame[frame["stack_eligible"] == 1]
    no_stack = frame[frame["stack_eligible"] == 0]

    # -- parallel trends: did the two groups grow alike BEFORE the campaign? --
    trend_stat = stats.ttest_ind(stack["pre_growth"], no_stack["pre_growth"], equal_var=False)
    parallel_p = float(trend_stat.pvalue)

    # -- CUPED adjustment on each property's own pre-campaign trend ---------
    y = frame["growth"].to_numpy(dtype=float)
    x = frame["pre_growth"].to_numpy(dtype=float)
    theta = float(np.cov(y, x, ddof=1)[0, 1] / np.var(x, ddof=1)) if np.var(x) > 0 else 0.0
    y_adj = y - theta * (x - x.mean())
    variance_reduction = 1.0 - float(np.var(y_adj, ddof=1) / np.var(y, ddof=1))

    frame = frame.assign(growth_adj=y_adj)
    stack_adj = frame.loc[frame["stack_eligible"] == 1, "growth_adj"].to_numpy()
    no_stack_adj = frame.loc[frame["stack_eligible"] == 0, "growth_adj"].to_numpy()

    diff = float(stack_adj.mean() - no_stack_adj.mean())
    se = float(
        np.sqrt(
            stack_adj.var(ddof=1) / stack_adj.size + no_stack_adj.var(ddof=1) / no_stack_adj.size
        )
    )
    test = stats.ttest_ind(stack_adj, no_stack_adj, equal_var=False)
    z = float(stats.norm.ppf(1 - cfg.model.alpha / 2))

    # Log-point differences convert to a multiplicative effect.
    return StackingResult(
        n_stack=int(stack.shape[0]),
        n_no_stack=int(no_stack.shape[0]),
        stack_uplift=float(np.expm1(stack_adj.mean())),
        no_stack_uplift=float(np.expm1(no_stack_adj.mean())),
        incremental_stacking_value=float(np.expm1(diff)),
        ci=(float(np.expm1(diff - z * se)), float(np.expm1(diff + z * se))),
        p_value=float(test.pvalue),
        parallel_trends_p=parallel_p,
        variance_reduction=variance_reduction,
    )

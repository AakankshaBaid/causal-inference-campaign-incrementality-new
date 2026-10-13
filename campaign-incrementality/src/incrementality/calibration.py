"""Calibrating how wide the reported ranges need to be.

The model's own ranges come from a rolling-origin backtest, which never sees
the campaign window. Measured on simulated campaigns with known answers they
came out too narrow: on campaigns where nothing happened the 90% range
contained the truth only 73% of the time, and 4 of 26 were wrongly declared
wins. This module turns that measurement into a correction.

Split-conformal calibration. For each calibration campaign, ask by what factor
BOTH half-widths of its range would have had to grow to cover the truth. That
is its score. The factor that delivers 90% coverage is the
``ceil((n + 1) * 0.90)``-th smallest score, which carries a finite-sample
guarantee when new campaigns are exchangeable with the calibration ones.

The guarantee is only as good as that exchangeability. The factor is fitted on
simulated campaigns from this project's own generator, so it is calibrated
for that family, not for any live business. On live data, recompute it from
historical campaigns or placebo windows (``studies/interval_calibration_study.py``).
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd


def interval_scores(frame: pd.DataFrame) -> pd.Series:
    """Factor by which both half-widths must grow to cover the truth.

    Needs columns ``estimate``, ``error`` (estimate minus truth), ``ci_low``
    and ``ci_high``. A score at or below 1 means the range already covered it.
    """
    lower = frame["estimate"] - frame["ci_low"]
    upper = frame["ci_high"] - frame["estimate"]
    error = frame["error"]
    score = np.where(error > 0, error / lower, np.where(error < 0, -error / upper, 0.0))
    return pd.Series(score, index=frame.index)


def calibration_factor(frame: pd.DataFrame, alpha: float = 0.10) -> float:
    """Split-conformal widening factor for ``1 - alpha`` coverage."""
    scores = np.sort(interval_scores(frame).to_numpy(dtype=float))
    n = len(scores)
    k = math.ceil((n + 1) * (1.0 - alpha))
    if k > n:
        raise ValueError(
            f"{n} calibration campaigns cannot support {1 - alpha:.0%} coverage; "
            f"need at least {math.ceil(1 / alpha) - 1 + 1}"
        )
    return float(scores[k - 1])


def worst_arm_factor(frame: pd.DataFrame, arm_col: str = "arm", alpha: float = 0.10) -> float:
    """Largest of the per-arm factors, so coverage holds whether or not there is an effect.

    A range claiming 90% has to be right on campaigns where nothing happened AND
    on campaigns with a real effect. Measured, the two are not alike: with a real
    effect the estimate's error is larger and biased upward, so it needs a wider
    range. Fitting one factor to a mixture lets the easier arm dominate and
    under-covers the harder one, which is exactly what a first, pooled attempt
    did (it fixed the no-effect arm and left the effect arm at 75%). Taking the
    maximum guarantees each arm its coverage; the cost is ranges that are
    conservative when nothing is happening.
    """
    return max(calibration_factor(group, alpha=alpha) for _, group in frame.groupby(arm_col))


def round_up(value: float, digits: int = 2) -> float:
    """Round UP, never down: a calibrated range must not be narrowed by rounding."""
    scale = 10**digits
    return math.ceil(value * scale - 1e-9) / scale


def inflate_interval(point: float, low: float, high: float, factor: float) -> tuple[float, float]:
    """Widen a range about its point estimate; the estimate itself never moves."""
    if factor < 1.0:
        raise ValueError(f"interval_inflation must be >= 1, got {factor}")
    return (
        point - factor * max(point - low, 0.0),
        point + factor * max(high - point, 0.0),
    )

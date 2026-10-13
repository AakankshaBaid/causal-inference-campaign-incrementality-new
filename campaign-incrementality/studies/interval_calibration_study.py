"""Calibrate and validate the width of the reported ranges.

Why this exists. Measured on simulated campaigns with known answers, the model's
own 90% ranges were too narrow: on campaigns where nothing happened they
contained the truth 73% of the time, and 4 of 26 were wrongly declared wins.

The correction is one number, the widening factor in each campaign config
(``model.interval_inflation``). This study derives it and then tests it on data
it never saw.

    calibrate   split-conformal factor from the accuracy study's raw ranges
                (``outputs/tables/recovery_study_draws.csv``: the selected design
                on effect campaigns, plus the zero-effect campaigns)
    validate    simulate FRESH campaigns (seeds the calibration never used),
                record their raw ranges
    summary     apply the factor to those fresh campaigns and report coverage,
                false-win rate and detection, raw against calibrated

Validation uses the production setting of 2,000 bootstrap draws. The calibration
pool used 400; bootstrap count affects quantile noise, not the average width.

Scope. The factor is calibrated for this project's simulator. On live data,
recompute it from historical campaigns or placebo windows.

    python studies/interval_calibration_study.py calibrate
    python studies/interval_calibration_study.py validate --arm zero_effect --seeds 100-129
    python studies/interval_calibration_study.py validate --arm effect --seeds 100-115
    python studies/interval_calibration_study.py summary
"""

from __future__ import annotations

import argparse
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent / "src"))
sys.path.insert(0, str(HERE))

from recovery_study import ARMS, HEADLINE_SPEC, SPECS, _estimate, _simulate  # noqa: E402

from incrementality.calibration import (  # noqa: E402
    calibration_factor,
    inflate_interval,
    round_up,
    worst_arm_factor,
)
from incrementality.config import load_cohort  # noqa: E402

warnings.filterwarnings("ignore")
TABLES = Path("outputs/tables")
POOL = TABLES / "recovery_study_draws.csv"
VALIDATION = TABLES / "interval_validation_draws.csv"
SUMMARY = TABLES / "interval_validation_summary.csv"


def _seeds(text: str) -> list[int]:
    lo, _, hi = text.partition("-")
    return list(range(int(lo), int(hi or lo) + 1))


COLS = ["arm", "seed", "truth", "estimate", "error", "ci_low", "ci_high"]


def calibration_pool(root: Path = Path(".")) -> pd.DataFrame:
    """Every campaign with a raw range and a known answer.

    The accuracy study's selected design (effect and no-effect arms) plus the
    fresh validation campaigns from ``validate``.
    """
    tables = root / "outputs/tables"
    old = pd.read_csv(tables / "recovery_study_draws.csv", keep_default_na=False, na_values=[""])
    keep = ((old["arm"] == "effect") & (old["specification"] == HEADLINE_SPEC)) | (
        old["arm"] == "zero_effect"
    )
    parts = [old[keep][COLS]]
    fresh = tables / "interval_validation_draws.csv"
    if fresh.exists():
        parts.append(pd.read_csv(fresh)[COLS])
    # Sorted, so the cross-validation below assigns the same folds whatever order
    # the study CSVs were written in. Re-running a study replaces rows and appends
    # them at the end, which silently shifted the folds and the reported numbers.
    return pd.concat(parts, ignore_index=True).sort_values(["arm", "seed"]).reset_index(drop=True)


def round_one_pool() -> pd.DataFrame:
    """Only the original accuracy-study campaigns: the first calibration's data."""
    pool = calibration_pool()
    fresh = pd.read_csv(VALIDATION)[["arm", "seed"]]
    return pool[~pool.set_index(["arm", "seed"]).index.isin(fresh.set_index(["arm", "seed"]).index)]


def cmd_calibrate(_args) -> int:
    pool = calibration_pool()
    print(f"{len(pool)} calibration campaigns")
    for arm, g in pool.groupby("arm"):
        print(f"  {arm:<12} n={len(g):<3} factor for 90% coverage: {calibration_factor(g):.3f}")
    final = worst_arm_factor(pool)
    print(f"worst-arm factor: {final:.3f}  ->  configured value {round_up(final):.2f}")
    return 0


def cmd_validate(args) -> int:
    cfg = load_cohort(args.config)
    truth, base = ARMS[args.arm]
    existing = pd.read_csv(VALIDATION) if VALIDATION.exists() else pd.DataFrame()
    rows = []
    started = time.time()
    for i in _seeds(args.seeds):
        seed = base + i
        treated, truth_lift = _simulate(cfg, seed, truth, "small")
        row = _estimate(cfg, seed, treated, truth_lift, SPECS[HEADLINE_SPEC], args.n_bootstrap)
        rows.append(
            {
                "arm": args.arm,
                **{
                    k: row[k]
                    for k in (
                        "seed",
                        "truth",
                        "estimate",
                        "error",
                        "ci_low",
                        "ci_high",
                        "backtest_mape",
                    )
                },
            }
        )
        fresh = pd.DataFrame(rows)
        keep = pd.DataFrame()
        if not existing.empty:
            keys = set(zip(fresh["arm"], fresh["seed"], strict=True))
            keep = existing[
                [(a, s) not in keys for a, s in zip(existing["arm"], existing["seed"], strict=True)]
            ]
        VALIDATION.parent.mkdir(parents=True, exist_ok=True)
        pd.concat([keep, fresh], ignore_index=True).to_csv(VALIDATION, index=False)
        print(f"  seed {seed} done ({time.time() - started:.0f}s)", flush=True)
    return 0


def _interval(n_hit: int, n: int) -> tuple[float, float]:
    ci = stats.binomtest(int(n_hit), int(n)).proportion_ci(0.95)
    return ci.low, ci.high


def _rates(frame: pd.DataFrame, factor: float, lows=None) -> dict:
    n = len(frame)
    lows = frame["ci_low"] if lows is None else lows
    out = {"n": n}
    for tag, lo_col, hi_col in (("raw", frame["ci_low"], frame["ci_high"]), ("cal", None, None)):
        if tag == "raw":
            lo, hi = lo_col, hi_col
        else:
            pairs = [
                inflate_interval(est, low, high, factor)
                for est, low, high in zip(
                    frame["estimate"], frame["ci_low"], frame["ci_high"], strict=True
                )
            ]
            lo, hi = (
                pd.Series([p[0] for p in pairs], index=frame.index),
                pd.Series([p[1] for p in pairs], index=frame.index),
            )
        cov = int(((lo <= frame["truth"]) & (frame["truth"] <= hi)).sum())
        win = int(((frame["estimate"] >= 0.01) & (lo > 0)).sum())
        cl, ch = _interval(cov, n)
        out.update(
            {
                f"coverage_{tag}": cov / n,
                f"coverage_{tag}_lo": cl,
                f"coverage_{tag}_hi": ch,
                f"win_rate_{tag}": win / n,
            }
        )
    return out


def cmd_summary(_args) -> int:
    rows = []
    # -- stage 1: the first calibration, validated on campaigns it never saw --
    first = calibration_factor(round_one_pool(), alpha=0.10)
    fresh = pd.read_csv(VALIDATION)[COLS]
    for arm, g in (
        ("zero_effect", fresh[fresh.arm == "zero_effect"]),
        ("effect", fresh[fresh.arm == "effect"]),
    ):
        rows.append(
            {
                "stage": "round 1: pooled factor on fresh campaigns",
                "group": arm,
                "factor": round_up(first),
                **_rates(g, round_up(first)),
            }
        )
    # -- stage 2: the final worst-arm factor, cross-validated on all campaigns --
    pool = calibration_pool()
    final = round_up(worst_arm_factor(pool))
    rng = np.random.default_rng(0)
    folds = np.array_split(rng.permutation(len(pool)), 10)
    held = []
    factors = []
    for fold in folds:
        train = pool.drop(pool.index[fold])
        f = round_up(worst_arm_factor(train))
        factors.append(f)
        test = pool.iloc[fold].copy()
        test["fold_factor"] = f
        held.append(test)
    held = pd.concat(held)
    for arm, g in held.groupby("arm"):
        parts = [_rates(g[g.fold_factor == f], f) for f in sorted(g.fold_factor.unique())]
        n = sum(p["n"] for p in parts)
        agg = {"n": n}
        for k in parts[0]:
            if k != "n":
                agg[k] = sum(p[k] * p["n"] for p in parts) / n
        cov = int(round(agg["coverage_cal"] * n))
        agg["coverage_cal_lo"], agg["coverage_cal_hi"] = _interval(cov, n)
        rows.append(
            {
                "stage": "final: worst-arm factor, 10-fold cross-validated",
                "group": arm,
                "factor": final,
                **agg,
            }
        )
    frame = pd.DataFrame(rows)
    frame.to_csv(SUMMARY, index=False)
    print(
        f"round 1 (pooled factor {round_up(first):.2f} fitted on {len(round_one_pool())} campaigns, tested on {len(fresh)} fresh ones):"
    )
    for r in rows[:2]:
        print(
            f"  {r['group']:<12} n={r['n']:<3} range holds truth: raw {r['coverage_raw']:.0%} -> {r['coverage_cal']:.0%} | declared wins: raw {r['win_rate_raw']:.0%} -> {r['win_rate_cal']:.0%}"
        )
    print(
        f"\nfinal worst-arm factor {final:.2f} fitted on {len(pool)} campaigns; fold factors {min(factors):.2f}-{max(factors):.2f}; out-of-sample (10-fold) results:"
    )
    for r in rows[2:]:
        print(
            f"  {r['group']:<12} n={r['n']:<3} range holds truth: raw {r['coverage_raw']:.0%} -> {r['coverage_cal']:.0%} (95% CI {r['coverage_cal_lo']:.0%}-{r['coverage_cal_hi']:.0%}) | declared wins: raw {r['win_rate_raw']:.0%} -> {r['win_rate_cal']:.0%}"
        )
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("calibrate").set_defaults(fn=cmd_calibrate)
    v = sub.add_parser("validate")
    v.add_argument("--config", type=Path, default=Path("configs/mid_year_sale_2025.yaml"))
    v.add_argument("--arm", choices=tuple(ARMS), required=True)
    v.add_argument("--seeds", required=True, help="e.g. 100-129 (seed = arm base + index)")
    v.add_argument("--n-bootstrap", type=int, default=2000)
    v.set_defaults(fn=cmd_validate)
    sub.add_parser("summary").set_defaults(fn=cmd_summary)
    args = parser.parse_args(argv)
    return args.fn(args)


if __name__ == "__main__":
    raise SystemExit(main())

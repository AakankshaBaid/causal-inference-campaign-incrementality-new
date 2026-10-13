"""Does a longer pre-period explain the Black Friday error?

Hypothesis. Last year's campaign window sits exactly on the holiday weeks. With
78 weeks of history there is only one prior holiday season, so the holiday
effect and last year's campaign effect are collinear and cannot be separated.
If that were the cause, a second prior season (104 weeks) should shrink the
error on a Black Friday window.

Result. It did not. Bias and typical error were about the same with 78 and 104
weeks, so the hypothesis is not supported and the cause of the Black Friday
miss remains unidentified. The study is committed so the negative result is
reproducible rather than asserted.

Usage:
    python studies/history_length_study.py --seeds 301-306
"""

from __future__ import annotations

import argparse
import sys
import warnings
from dataclasses import replace
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from incrementality.config import load_cohort
from incrementality.counterfactual import get_backend
from incrementality.inference import estimate_uplift
from incrementality.simulate import (
    GroundTruth,
    SimulationSpec,
    aggregate_to_cohort,
    simulate_panel,
    split_control_pool,
    true_average_lift,
)
from incrementality.validation import _design_for

warnings.filterwarnings("ignore")


def _seeds(text: str) -> list[int]:
    lo, _, hi = text.partition("-")
    return list(range(int(lo), int(hi or lo) + 1))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path("configs/black_friday_2024.yaml"))
    parser.add_argument("--seeds", default="301-306")
    parser.add_argument("--histories", default="78,104")
    parser.add_argument("--out", type=Path, default=Path("outputs/tables/history_length_study.csv"))
    args = parser.parse_args()

    base = load_cohort(args.config)
    rows = []
    for history in (int(h) for h in args.histories.split(",")):
        cfg = replace(base, pre_weeks=history)
        for seed in _seeds(args.seeds):
            panel = split_control_pool(
                simulate_panel(
                    SimulationSpec(
                        activation_week=str(cfg.activation_week.date()),
                        pre_weeks=history,
                        post_weeks=cfg.post_weeks + 2,
                        seed=seed,
                        truth=GroundTruth(),
                        n_treated=1_200,
                        n_compset=1_200,
                        n_distant=1_500,
                    )
                ),
                seed=seed + 1,
            )
            series = aggregate_to_cohort(panel, cfg.outcomes)
            treated = series[series["cohort"] == "treated"].reset_index(drop=True)
            truth = true_average_lift(panel, cfg.post_start, cfg.post_end)
            result = estimate_uplift(
                get_backend("bsts"),
                _design_for(treated, "gbv", cfg),
                alpha=0.10,
                n_bootstrap=300,
            )
            rows.append(
                {
                    "history_weeks": history,
                    "seed": seed,
                    "truth": truth,
                    "estimate": result.relative_uplift,
                    "error": result.relative_uplift - truth,
                    "ci_low": result.ci_relative[0],
                    "ci_high": result.ci_relative[1],
                    "covered": bool(result.ci_relative[0] <= truth <= result.ci_relative[1]),
                }
            )
            args.out.parent.mkdir(parents=True, exist_ok=True)
            pd.DataFrame(rows).to_csv(args.out, index=False)

    frame = pd.DataFrame(rows)
    print(f"{'history':>8} {'n':>3} {'bias':>8} {'rmse':>8} {'coverage':>9}")
    for history, group in frame.groupby("history_weeks"):
        err = group["error"] * 100
        print(
            f"{history:>8} {len(group):>3} {err.mean():>+7.2f}pp "
            f"{np.sqrt((err**2).mean()):>7.2f}pp {group['covered'].mean():>8.0%}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

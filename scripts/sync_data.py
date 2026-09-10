"""Copy the aggregated products from the MATLAB output tree into dashboard/data.

The MATLAB driver (matlab_export/exportForDashboard.m) already does this. This
script exists for the case where the CSVs were regenerated without rerunning
the driver, and for CI.

    python dashboard/scripts/sync_data.py [--source 8postprocess] [--dry-run]
"""
from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

APP_DIR = Path(__file__).resolve().parent.parent
REPO_ROOT = APP_DIR.parent

FROM_CSV_DIR = [
    "regional_series.csv",
    "popweighted_annual.csv",
    "seasonal_means_trends.csv",
    "regional_trends.csv",
    "trend_ols_regional.csv",
    "trend_twoperiod_regional.csv",
    "peak_month_trend.csv",
    "country_trends.csv",
    "exposure_by_threshold.csv",
    "exposure_trends.csv",
]
FROM_ROOT = ["ref_published_trends.csv"]

# Written only by the MATLAB export step -- never copied from elsewhere.
MATLAB_ONLY = ["country_series.csv", "grid_annual.parquet"]


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--source", default=str(REPO_ROOT / "8postprocess"),
                    help="post-processing output directory")
    ap.add_argument("--dest", default=str(APP_DIR / "data"),
                    help="dashboard data directory")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args(argv)

    src = Path(args.source)
    dest = Path(args.dest)
    if not src.is_dir():
        print(f"source not found: {src}", file=sys.stderr)
        return 2
    dest.mkdir(parents=True, exist_ok=True)

    copied, missing = 0, []
    for name in FROM_CSV_DIR:
        s = src / "csv" / name
        if s.exists():
            if not args.dry_run:
                shutil.copy2(s, dest / name)
            copied += 1
            print(f"  {name}")
        else:
            missing.append(str(s))

    for name in FROM_ROOT:
        s = src / name
        if s.exists():
            if not args.dry_run:
                shutil.copy2(s, dest / name)
            copied += 1
            print(f"  {name}")
        else:
            missing.append(str(s))

    print(f"\n{'would copy' if args.dry_run else 'copied'} {copied} file(s) -> {dest}")
    if missing:
        print("\nnot found:")
        for m in missing:
            print(f"  {m}")

    absent = [n for n in MATLAB_ONLY if not (dest / n).exists()]
    if absent:
        print("\nstill needed (MATLAB only):")
        for n in absent:
            print(f"  {n}")
        print("  -> run matlab_export/exportForDashboard.m from the repo root")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())

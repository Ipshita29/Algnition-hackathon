"""Loads the trained pickle + features.parquet, runs the tribunal, and
writes predictions.csv in the exact required column order.

CLI: python src/predict.py --features features.parquet --model ./pickle/model.pkl --output ./output/predictions.csv
"""
import argparse
import os

import pandas as pd

from models.tribunal import ForecastingTribunal

# The judged output format - predictions.csv must contain EXACTLY these
# columns in exactly this order. The submission guide is explicit that the
# scoring is automated and "producing the right answers in the wrong format
# scores zero", so nothing may be appended here.
REQUIRED_COLUMNS = [
    "channel",
    "campaign_type",
    "campaign_name",
    "period_days",
    "revenue_p10",
    "revenue_p50",
    "revenue_p90",
    "roas_p10",
    "roas_p50",
    "roas_p90",
    "disagreement_pct",
    "uncertainty_level",
]

# Written to a SEPARATE predictions_detail.csv (same directory as the scored
# output) for the War Room UI's Tribunal Verdict Panel: the required columns
# plus each model's own P50 for the agreement badges. prophet_p50 is blank
# when Prophet was skipped for a campaign; all three are blank for
# naive-fallback rows.
EXTRA_COLUMNS = ["prophet_p50", "xgb_p50", "ridge_p50"]

DETAIL_COLUMNS = REQUIRED_COLUMNS + EXTRA_COLUMNS
DETAIL_FILENAME = "predictions_detail.csv"


def load_budget_overrides(path):
    """Optional future-budget input: a CSV with columns channel,
    campaign_name, daily_budget. Returns {(channel, campaign_name): daily_budget}
    for tribunal.predict()'s future_spend_overrides. Campaigns not listed keep
    the default trailing-28-day average spend scenario.
    """
    budgets = pd.read_csv(path)
    missing = [c for c in ("channel", "campaign_name", "daily_budget") if c not in budgets.columns]
    if missing:
        raise ValueError(f"{path} is missing required column(s): {missing}")
    return {
        (row.channel, row.campaign_name): float(row.daily_budget)
        for row in budgets.itertuples(index=False)
    }


def main():
    parser = argparse.ArgumentParser(description="Run the tribunal and write predictions.csv")
    parser.add_argument("--features", required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument(
        "--budgets",
        help="Optional CSV (channel,campaign_name,daily_budget) of future media "
        "budgets to forecast against instead of each campaign's recent spend",
    )
    args = parser.parse_args()

    df = pd.read_parquet(args.features)
    tribunal = ForecastingTribunal.load(args.model)

    overrides = load_budget_overrides(args.budgets) if args.budgets else None
    predictions = tribunal.predict(df, periods=(30, 60, 90), future_spend_overrides=overrides)

    rows = []
    for campaign_periods in predictions.values():
        for row in campaign_periods.values():
            rows.append(row)

    out_df = pd.DataFrame(rows)[DETAIL_COLUMNS]
    out_df = out_df.sort_values(["channel", "campaign_type", "campaign_name", "period_days"]).reset_index(drop=True)

    for col in ["revenue_p10", "revenue_p50", "revenue_p90", "roas_p10", "roas_p50", "roas_p90", *EXTRA_COLUMNS]:
        out_df[col] = out_df[col].round(2)
    out_df["disagreement_pct"] = out_df["disagreement_pct"].round(1)

    out_dir = os.path.dirname(args.output)
    os.makedirs(out_dir if out_dir else ".", exist_ok=True)

    # The scored file: exactly the required columns, nothing appended.
    out_df[REQUIRED_COLUMNS].to_csv(args.output, index=False)
    # The UI companion file with per-model P50s, next to the scored file.
    detail_path = os.path.join(out_dir if out_dir else ".", DETAIL_FILENAME)
    out_df.to_csv(detail_path, index=False)

    print(f"Wrote {len(out_df)} rows to {args.output} (+ per-model detail in {detail_path})")


if __name__ == "__main__":
    main()

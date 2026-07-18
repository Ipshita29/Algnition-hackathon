"""Fits the ForecastingTribunal on the raw channel CSVs and pickles it.

Not called from run.sh - this is the one-time (or re-run-when-data-changes)
training step. run.sh only calls generate_features.py and predict.py.

CLI: python src/train.py --data-dir ./data --out ./pickle/model.pkl
"""
import argparse

from generate_features import build_features
from models.tribunal import ForecastingTribunal


def main():
    parser = argparse.ArgumentParser(description="Train the ForecastingTribunal and save it as a pickle")
    parser.add_argument("--data-dir", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    df = build_features(args.data_dir)
    tribunal = ForecastingTribunal().fit(df)
    ForecastingTribunal.save(tribunal, args.out)

    # Never leave the pickle untested - confirm it loads back cleanly before reporting success.
    ForecastingTribunal.load(args.out)

    # campaign_name alone undercounts real campaigns: some names (e.g.
    # "Pmax_NTM_Campaign_01") legitimately exist in more than one channel.
    campaign_count = df.groupby(["channel", "campaign_name"]).ngroups
    modeled_count = len(tribunal.campaign_info)
    print(
        f"Trained on {len(df)} rows across {campaign_count} campaigns "
        f"({modeled_count} fitted with models, {campaign_count - modeled_count} too sparse - "
        "will use the naive fallback at predict time). "
        f"Saved and verified pickle at {args.out}"
    )


if __name__ == "__main__":
    main()

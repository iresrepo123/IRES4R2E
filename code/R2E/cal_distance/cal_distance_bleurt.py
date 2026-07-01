                      
"""Calculate reference-based BLEURT scores for RQ1."""

import argparse
from pathlib import Path

from cal_distance_common import (
    LEVELS,
    load_level_records,
    save_level_scores,
    save_summary,
    subset_ids,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=Path("BERTScore"))
    parser.add_argument("--input-prefix", default="BERTScore")
    parser.add_argument("--sample-file", type=Path, default=Path("human_eval_target_500.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("RQ1/BLEURT"))
    parser.add_argument("--checkpoint", required=True, help="Path to BLEURT-20")
    parser.add_argument("--batch-size", type=int, default=16)
    args = parser.parse_args()

    try:
        from bleurt import score as bleurt_score
    except ImportError as exc:
        raise RuntimeError("Install the official google-research/bleurt package") from exc

    scorer = bleurt_score.BleurtScorer(args.checkpoint)
    selected_ids = subset_ids(args.sample_file)
    means = {}
    for level in LEVELS:
        records = load_level_records(args.input_dir, args.input_prefix, level, selected_ids)
        scores = scorer.score(
            references=[record["reference"] for record in records],
            candidates=[record["summary"] for record in records],
            batch_size=args.batch_size,
        )
        means[level] = sum(scores) / len(scores)
        path = save_level_scores(args.output_dir, "BLEURT", level, records, "bleurt", scores)
        print(f"L{level}: mean={means[level]:.6f}; wrote {path}")
    print(save_summary(args.output_dir, "BLEURT", "bleurt", means, len(selected_ids)))


if __name__ == "__main__":
    main()

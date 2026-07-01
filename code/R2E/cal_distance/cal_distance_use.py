                      
"""Calculate reference-based Universal Sentence Encoder similarity for RQ1."""

import argparse
from pathlib import Path

from cal_distance_common import (
    LEVELS,
    batches,
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
    parser.add_argument("--output-dir", type=Path, default=Path("RQ1/USE"))
    parser.add_argument("--model", default="https://tfhub.dev/google/universal-sentence-encoder/4")
    parser.add_argument("--batch-size", type=int, default=64)
    args = parser.parse_args()

    try:
        import numpy as np
        import tensorflow_hub as hub
    except ImportError as exc:
        raise RuntimeError("Install tensorflow and tensorflow-hub") from exc

    model = hub.load(args.model)
    selected_ids = subset_ids(args.sample_file)
    means = {}
    for level in LEVELS:
        records = load_level_records(args.input_dir, args.input_prefix, level, selected_ids)
        scores = []
        for chunk in batches(records, args.batch_size):
            left = np.array(
                model([record["summary"] for record in chunk]), copy=True
            )
            right = np.array(
                model([record["reference"] for record in chunk]), copy=True
            )
            left = left / np.maximum(
                np.linalg.norm(left, axis=1, keepdims=True), 1e-12
            )
            right = right / np.maximum(
                np.linalg.norm(right, axis=1, keepdims=True), 1e-12
            )
            scores.extend((left * right).sum(axis=1).tolist())
        means[level] = sum(scores) / len(scores)
        path = save_level_scores(args.output_dir, "USE", level, records, "use_cosine", scores)
        print(f"L{level}: mean={means[level]:.6f}; wrote {path}")
    print(save_summary(args.output_dir, "USE", "use_cosine", means, len(selected_ids)))


if __name__ == "__main__":
    main()

                      
"""Calculate reference-based SentenceBERT cosine similarity for RQ1."""

import argparse
import os
from pathlib import Path

from cal_distance_common import (
    LEVELS,
    load_level_records,
    save_level_scores,
    save_summary,
    subset_ids,
)

                                                                              
                                                                                 
os.environ.setdefault("USE_TF", "0")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=Path("BERTScore"))
    parser.add_argument("--input-prefix", default="BERTScore")
    parser.add_argument("--sample-file", type=Path, default=Path("human_eval_target_500.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("RQ1/SentenceBERT"))
    parser.add_argument("--model", default="sentence-transformers/all-mpnet-base-v2")
    parser.add_argument("--batch-size", type=int, default=32)
    parser.add_argument("--device", default=None)
    args = parser.parse_args()

    try:
        from sentence_transformers import SentenceTransformer
    except ImportError as exc:
        raise RuntimeError("Install sentence-transformers") from exc

    model = SentenceTransformer(args.model, device=args.device)
    selected_ids = subset_ids(args.sample_file)
    means = {}
    for level in LEVELS:
        records = load_level_records(args.input_dir, args.input_prefix, level, selected_ids)
        left = model.encode(
            [record["summary"] for record in records],
            batch_size=args.batch_size,
            normalize_embeddings=True,
            show_progress_bar=True,
        )
        right = model.encode(
            [record["reference"] for record in records],
            batch_size=args.batch_size,
            normalize_embeddings=True,
            show_progress_bar=True,
        )
        scores = (left * right).sum(axis=1).tolist()
        means[level] = sum(scores) / len(scores)
        path = save_level_scores(
            args.output_dir, "SentenceBERT", level, records, "sentencebert_cosine", scores
        )
        print(f"L{level}: mean={means[level]:.6f}; wrote {path}")
    print(save_summary(args.output_dir, "SentenceBERT", "sentencebert_cosine", means, len(selected_ids)))


if __name__ == "__main__":
    main()

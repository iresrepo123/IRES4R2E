                      
"""Calculate reference-based InferSent cosine similarity for RQ1."""

import argparse
import sys
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
    parser.add_argument("--output-dir", type=Path, default=Path("RQ1/InferSent"))
    parser.add_argument("--repo", type=Path, required=True, help="Cloned facebookresearch/InferSent")
    parser.add_argument("--checkpoint", type=Path, required=True, help="infersent2.pkl")
    parser.add_argument("--word-vectors", type=Path, required=True, help="crawl-300d-2M.vec")
    parser.add_argument("--batch-size", type=int, default=64)
    parser.add_argument("--device", default="cpu")
    args = parser.parse_args()

    try:
        import numpy as np
        import torch
    except ImportError as exc:
        raise RuntimeError("Install numpy, torch, and nltk") from exc

    sys.path.insert(0, str(args.repo.resolve()))
    from models import InferSent

    params = {
        "bsize": args.batch_size,
        "word_emb_dim": 300,
        "enc_lstm_dim": 2048,
        "pool_type": "max",
        "dpout_model": 0.0,
        "version": 2,
    }
    model = InferSent(params)
    state = torch.load(args.checkpoint, map_location=args.device)
    model.load_state_dict(state)
    model.set_w2v_path(str(args.word_vectors))
    model.to(args.device)

    selected_ids = subset_ids(args.sample_file)
    all_records = {
        level: load_level_records(args.input_dir, args.input_prefix, level, selected_ids)
        for level in LEVELS
    }
    vocabulary_texts = []
    for records in all_records.values():
        vocabulary_texts.extend(record["summary"] for record in records)
        vocabulary_texts.extend(record["reference"] for record in records)
    model.build_vocab(vocabulary_texts, tokenize=True)

    means = {}
    for level, records in all_records.items():
        left = model.encode(
            [record["summary"] for record in records],
            bsize=args.batch_size,
            tokenize=True,
        )
        right = model.encode(
            [record["reference"] for record in records],
            bsize=args.batch_size,
            tokenize=True,
        )
        left /= np.maximum(np.linalg.norm(left, axis=1, keepdims=True), 1e-12)
        right /= np.maximum(np.linalg.norm(right, axis=1, keepdims=True), 1e-12)
        scores = (left * right).sum(axis=1).tolist()
        means[level] = sum(scores) / len(scores)
        path = save_level_scores(
            args.output_dir, "InferSent", level, records, "infersent_cosine", scores
        )
        print(f"L{level}: mean={means[level]:.6f}; wrote {path}")
    print(save_summary(args.output_dir, "InferSent", "infersent_cosine", means, len(selected_ids)))


if __name__ == "__main__":
    main()

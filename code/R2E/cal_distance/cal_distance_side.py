                      
"""Calculate reference-free SIDE code-summary cosine similarity for RQ1."""

import argparse
from pathlib import Path

from cal_distance_common import (
    LEVELS,
    batches,
    load_json,
    load_level_records,
    method_code,
    save_level_scores,
    save_summary,
    subset_ids,
)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=Path("BERTScore"))
    parser.add_argument("--input-prefix", default="BERTScore")
    parser.add_argument("--sample-file", type=Path, default=Path("human_eval_target_500.json"))
    parser.add_argument("--output-dir", type=Path, default=Path("RQ1/SIDE"))
    parser.add_argument("--checkpoint", required=True, help="Official SIDE checkpoint directory")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--device", default="cuda")
    parser.add_argument("--max-length", type=int, default=512)
    args = parser.parse_args()

    try:
        import torch
        import torch.nn.functional as functional
        from transformers import AutoModel, AutoTokenizer
    except ImportError as exc:
        raise RuntimeError("Install torch and transformers") from exc

    targets = load_json(args.sample_file)
    code_by_id = {record["sample_id"]: method_code(record) for record in targets}
    if any(not code for code in code_by_id.values()):
        raise ValueError("At least one selected target has no source code")

    tokenizer = AutoTokenizer.from_pretrained(args.checkpoint)
    model = AutoModel.from_pretrained(args.checkpoint).to(args.device).eval()

    def encode(texts):
        encoded = tokenizer(
            texts,
            padding=True,
            truncation=True,
            max_length=args.max_length,
            return_tensors="pt",
        ).to(args.device)
        with torch.no_grad():
            output = model(**encoded)[0]
        mask = encoded["attention_mask"].unsqueeze(-1).expand(output.size()).float()
        pooled = torch.sum(output * mask, dim=1) / torch.clamp(mask.sum(dim=1), min=1e-9)
        return functional.normalize(pooled, p=2, dim=1)

    selected_ids = subset_ids(args.sample_file)
    means = {}
    for level in LEVELS:
        records = load_level_records(args.input_dir, args.input_prefix, level, selected_ids)
        scores = []
        for chunk in batches(records, args.batch_size):
            code_embeddings = encode([code_by_id[record["sample_id"]] for record in chunk])
            summary_embeddings = encode([record["summary"] for record in chunk])
            scores.extend(
                (code_embeddings * summary_embeddings).sum(dim=1).detach().cpu().tolist()
            )
        means[level] = sum(scores) / len(scores)
        path = save_level_scores(args.output_dir, "SIDE", level, records, "side", scores)
        print(f"L{level}: mean={means[level]:.6f}; wrote {path}")
    print(save_summary(args.output_dir, "SIDE", "side", means, len(selected_ids)))


if __name__ == "__main__":
    main()

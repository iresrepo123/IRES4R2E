                      
"""Calculate BERTScore F1 for L1-L9 summaries."""

import argparse

from metric_common import LEVELS, load_level_records, save_level_scores, save_summary


def main():
    parser = argparse.ArgumentParser(description="Calculate BERTScore F1 for prepared L1-L9 JSON files.")
    parser.add_argument("--input-dir", default="BERTScore")
    parser.add_argument("--model-type", default="microsoft/deberta-xlarge-mnli")
    parser.add_argument("--batch-size", type=int, default=16)
    parser.add_argument("--device", default=None, help="e.g. cuda, cuda:0, or cpu; default is package auto-detection")
    parser.add_argument(
        "--num-layers",
        type=int,
        default=None,
        help="Required when --model-type is a local directory; DeBERTa-xlarge-MNLI uses 24.",
    )
    parser.add_argument("--rescale-with-baseline", action="store_true")
    args = parser.parse_args()

    try:
        from bert_score import score as bertscore
    except ImportError as exc:
        raise RuntimeError("Install BERTScore first: pip install bert-score") from exc

    means = {}
    for level in LEVELS:
        _, records = load_level_records(args.input_dir, "BERTScore", level)
        candidates = [record["summary"] for record in records]
        references = [record["reference"] for record in records]
        _, _, f1 = bertscore(
            candidates,
            references,
            lang="en",
            model_type=args.model_type,
            batch_size=args.batch_size,
            device=args.device,
            num_layers=args.num_layers,
            rescale_with_baseline=args.rescale_with_baseline,
            verbose=True,
        )
        scores = f1.detach().cpu().tolist()
        means[level] = sum(scores) / len(scores)
        output_path = save_level_scores(args.input_dir, "BERTScore", level, records, "bertscore_f1", scores)
        print(f"L{level}: mean={means[level]:.6f}; wrote {output_path}")

    print(f"Summary: {save_summary(args.input_dir, 'BERTScore', 'bertscore_f1', means)}")


if __name__ == "__main__":
    main()

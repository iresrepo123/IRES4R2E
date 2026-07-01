                      
"""Calculate sentence-level smoothed BLEU-4 for L1-L9 summaries."""

import argparse
import re

from metric_common import LEVELS, load_level_records, save_level_scores, save_summary


def tokenize(text: str):
    return re.findall(r"[A-Za-z0-9_]+|[^\w\s]", text.lower())


def main():
    parser = argparse.ArgumentParser(description="Calculate BLEU-4 for prepared L1-L9 JSON files.")
    parser.add_argument("--input-dir", default="BLEU-4")
    args = parser.parse_args()

    try:
        from nltk.translate.bleu_score import SmoothingFunction, sentence_bleu
    except ImportError as exc:
        raise RuntimeError("Install NLTK first: pip install nltk") from exc

    smoothing = SmoothingFunction().method1
    means = {}
    for level in LEVELS:
        _, records = load_level_records(args.input_dir, "BLEU-4", level)
        scores = [
            sentence_bleu(
                [tokenize(record["reference"])],
                tokenize(record["summary"]),
                weights=(0.25, 0.25, 0.25, 0.25),
                smoothing_function=smoothing,
            )
            for record in records
        ]
        means[level] = sum(scores) / len(scores)
        output_path = save_level_scores(args.input_dir, "BLEU-4", level, records, "bleu_4", scores)
        print(f"L{level}: mean={means[level]:.6f}; wrote {output_path}")

    print(f"Summary: {save_summary(args.input_dir, 'BLEU-4', 'bleu_4', means)}")


if __name__ == "__main__":
    main()

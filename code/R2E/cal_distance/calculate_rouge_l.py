                      
"""Calculate sentence-level ROUGE-L F1 for L1-L9 summaries."""

import argparse

from metric_common import LEVELS, load_level_records, save_level_scores, save_summary


def main():
    parser = argparse.ArgumentParser(description="Calculate ROUGE-L F1 for prepared L1-L9 JSON files.")
    parser.add_argument("--input-dir", default="ROUGE-L")
    args = parser.parse_args()

    try:
        from rouge_score import rouge_scorer
    except ImportError as exc:
        raise RuntimeError("Install rouge-score first: pip install rouge-score") from exc

    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)
    means = {}
    for level in LEVELS:
        _, records = load_level_records(args.input_dir, "ROUGE-L", level)
        scores = [
            scorer.score(record["reference"], record["summary"])["rougeL"].fmeasure
            for record in records
        ]
        means[level] = sum(scores) / len(scores)
        output_path = save_level_scores(args.input_dir, "ROUGE-L", level, records, "rouge_l_f1", scores)
        print(f"L{level}: mean={means[level]:.6f}; wrote {output_path}")

    print(f"Summary: {save_summary(args.input_dir, 'ROUGE-L', 'rouge_l_f1', means)}")


if __name__ == "__main__":
    main()

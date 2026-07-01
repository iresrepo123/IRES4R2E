                      
"""Calculate sentence-level METEOR for L1-L9 summaries."""

import argparse
import re

from metric_common import LEVELS, load_level_records, save_level_scores, save_summary


def tokenize(text: str):
    return re.findall(r"[A-Za-z0-9_]+|[^\w\s]", text.lower())


def main():
    parser = argparse.ArgumentParser(description="Calculate METEOR for prepared L1-L9 JSON files.")
    parser.add_argument("--input-dir", default="METEOR")
    args = parser.parse_args()

    try:
        from nltk.translate.meteor_score import meteor_score
    except ImportError as exc:
        raise RuntimeError("Install NLTK first: pip install nltk") from exc

    means = {}
    for level in LEVELS:
        _, records = load_level_records(args.input_dir, "METEOR", level)
        try:
            scores = [
                meteor_score([tokenize(record["reference"])], tokenize(record["summary"]))
                for record in records
            ]
        except LookupError as exc:
            raise RuntimeError(
                "METEOR requires NLTK WordNet data. Run: "
                "python -c \"import nltk; nltk.download('wordnet'); nltk.download('omw-1.4')\""
            ) from exc
        means[level] = sum(scores) / len(scores)
        output_path = save_level_scores(args.input_dir, "METEOR", level, records, "meteor", scores)
        print(f"L{level}: mean={means[level]:.6f}; wrote {output_path}")

    print(f"Summary: {save_summary(args.input_dir, 'METEOR', 'meteor', means)}")


if __name__ == "__main__":
    main()

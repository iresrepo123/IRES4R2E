                      
"""Create an evenly balanced sample from project-level JSON datasets."""

import argparse
import json
import random
from pathlib import Path


DEFAULT_INPUT_DIR = Path(__file__).parent / "projects_json_context"
DEFAULT_OUTPUT_FILE = Path(__file__).parent / "dataset.json"


def parse_args():
    parser = argparse.ArgumentParser(
        description="Sample methods as evenly as possible across all project JSON files."
    )
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_INPUT_DIR,
        help=f"Directory containing project JSON files (default: {DEFAULT_INPUT_DIR})",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT_FILE,
        help=f"Output JSON file (default: {DEFAULT_OUTPUT_FILE})",
    )
    parser.add_argument(
        "--sample-size",
        type=int,
        default=5000,
        help="Total number of methods to sample (default: 5000)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible sampling (default: 42)",
    )
    return parser.parse_args()


def allocate_samples(project_files, sample_size):
    base_count, remainder = divmod(sample_size, len(project_files))
    return {
        path: base_count + (index < remainder)
        for index, path in enumerate(project_files)
    }


def load_project(path):
    with path.open("r", encoding="utf-8") as file:
        data = json.load(file)

    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array")
    if not all(isinstance(item, dict) for item in data):
        raise ValueError(f"{path} contains a non-object record")
    return data


def build_sample(input_dir, sample_size, seed):
    project_files = sorted(input_dir.glob("*.json"))
    if not project_files:
        raise ValueError(f"No JSON files found in {input_dir}")
    if sample_size <= 0:
        raise ValueError("Sample size must be greater than zero")

    allocations = allocate_samples(project_files, sample_size)
    rng = random.Random(seed)
    sampled_records = []
    distribution = {}

    for path in project_files:
        project_data = load_project(path)
        requested = allocations[path]
        if len(project_data) < requested:
            raise ValueError(
                f"{path.name} has {len(project_data)} records, "
                f"but {requested} are required for balanced sampling"
            )

        selected_indices = rng.sample(range(len(project_data)), requested)
        distribution[path.name] = requested

        for source_index in selected_indices:
            record = dict(project_data[source_index])
            record["dataset_source_file"] = path.name
            sampled_records.append(record)

    rng.shuffle(sampled_records)
    for sample_id, record in enumerate(sampled_records):
        record["sample_id"] = sample_id

    return sampled_records, distribution


def main():
    args = parse_args()
    records, distribution = build_sample(
        input_dir=args.input_dir,
        sample_size=args.sample_size,
        seed=args.seed,
    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as file:
        json.dump(records, file, ensure_ascii=False, indent=2)

    print(f"Wrote {len(records)} methods to {args.output}")
    print(f"Random seed: {args.seed}")
    print("Project distribution:")
    for project, count in distribution.items():
        print(f"  {project}: {count}")


if __name__ == "__main__":
    main()

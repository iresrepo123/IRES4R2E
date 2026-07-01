import argparse
import glob
import json
import os
import re

import numpy as np
from rank_bm25 import BM25Okapi
from tqdm import tqdm


                                                   
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_TARGETS = os.path.join(SCRIPT_DIR, "dataset.json")
PROJECTS_DIR = os.path.join(SCRIPT_DIR, "projects_json_context")
OUTPUT_RETRIEVAL = os.path.join(SCRIPT_DIR, "bm25_retrieval_database.json")
                                                   


def simple_tokenizer(text):
    if not text:
        return []
    return [
        token.lower()
        for token in re.split(r"[^a-zA-Z0-9]+", text)
        if token.strip()
    ]


def construct_code_text(item):
    code = item.get("code", "") or item.get("raw_code", "")
    if not code:
        signature = item.get("method_signature", "")
        body = item.get("method_body_no_sig", "")
        if signature or body:
            code = f"{signature} {body}"
    if not code:
        code = item.get("func_name", "")
    return code


def method_identity(item, source_file=None):
    return (
        source_file or item.get("dataset_source_file", ""),
        item.get("file_path", ""),
        item.get("method_signature", ""),
        item.get("method_body_no_sig", ""),
    )


def load_json_array(path):
    with open(path, "r", encoding="utf-8") as file:
        try:
            data = json.load(file)
        except json.JSONDecodeError:
            file.seek(0)
            data = [json.loads(line) for line in file if line.strip()]

    if not isinstance(data, list):
        raise ValueError(f"{path} must contain a JSON array")
    return data


def load_project_indexes(projects_dir):
    project_files = sorted(glob.glob(os.path.join(projects_dir, "*.json")))
    if not project_files:
        raise FileNotFoundError(f"No project JSON files found in {projects_dir}")

    project_indexes = {}

    for project_path in tqdm(project_files, desc="Loading projects"):
        source_file = os.path.basename(project_path)
        corpus_items = []
        corpus_tokens = []
        identity_to_indices = {}

        for item in load_json_array(project_path):
            code_text = construct_code_text(item)
            tokens = simple_tokenizer(code_text)
            if not tokens:
                continue

            corpus_index = len(corpus_items)
            corpus_items.append(item)
            corpus_tokens.append(tokens)

            identity = method_identity(item, source_file)
            identity_to_indices.setdefault(identity, []).append(corpus_index)

        if not corpus_items:
            raise ValueError(f"{source_file} contains no valid methods")

        project_indexes[source_file] = {
            "bm25": BM25Okapi(corpus_tokens),
            "items": corpus_items,
            "identity_to_indices": identity_to_indices,
        }

    return project_indexes


def retrieve_top_k(target, bm25, corpus_items, identity_to_indices, top_k):
    query_tokens = simple_tokenizer(construct_code_text(target))
    if not query_tokens:
        return []

    scores = bm25.get_scores(query_tokens)

                                                                                   
    target_identity = method_identity(target)
    for corpus_index in identity_to_indices.get(target_identity, []):
        scores[corpus_index] = -np.inf

    candidate_count = min(top_k, len(scores))
    if candidate_count == 0:
        return []

    candidate_indices = np.argpartition(scores, -candidate_count)[-candidate_count:]
    ranked_indices = sorted(
        candidate_indices,
        key=lambda index: scores[index],
        reverse=True,
    )

    return [
        construct_code_text(corpus_items[index])
        for index in ranked_indices
        if np.isfinite(scores[index])
    ]


def parse_args():
    parser = argparse.ArgumentParser(
        description="Build project-local BM25 retrieval examples for reconstruction."
    )
    parser.add_argument("--targets", default=INPUT_TARGETS)
    parser.add_argument("--projects-dir", default=PROJECTS_DIR)
    parser.add_argument("--output", default=OUTPUT_RETRIEVAL)
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Maximum number of examples stored per target.",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if args.top_k < 1:
        raise ValueError("--top-k must be at least 1")
    if not os.path.isfile(args.targets):
        raise FileNotFoundError(f"Target dataset not found: {args.targets}")

    targets = load_json_array(args.targets)
    print(f"[*] Loaded {len(targets)} target methods")

    project_indexes = load_project_indexes(args.projects_dir)
    print(f"[*] Built {len(project_indexes)} project-level BM25 indexes")

    retrieval_dataset = []
    for target in tqdm(targets, desc=f"Retrieving Top-{args.top_k}"):
        sample_id = target.get("sample_id")
        if sample_id is None:
            raise ValueError("Every target method must have a sample_id")

        source_file = target.get("dataset_source_file")
        if source_file not in project_indexes:
            raise ValueError(
                f"Unknown dataset_source_file for sample {sample_id}: {source_file}"
            )

        project_index = project_indexes[source_file]
        retrieval_dataset.append(
            {
                "sample_id": sample_id,
                "bm25_topk": retrieve_top_k(
                    target,
                    project_index["bm25"],
                    project_index["items"],
                    project_index["identity_to_indices"],
                    args.top_k,
                ),
            }
        )

    with open(args.output, "w", encoding="utf-8") as file:
        json.dump(retrieval_dataset, file, indent=2, ensure_ascii=False)

    print(f"[*] Saved {len(retrieval_dataset)} records to {args.output}")


if __name__ == "__main__":
    main()

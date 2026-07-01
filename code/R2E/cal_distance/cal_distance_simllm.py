                      
"""Run the official SimLLM artifact and save per-example RQ1 scores."""

import argparse
import json
import os
import pickle
import string
import subprocess
import sys
from pathlib import Path

import numpy as np

from cal_distance_common import (
    LEVELS,
    load_level_records,
    save_level_scores,
    save_summary,
    subset_ids,
)


def clean_text(text):
    """Match scripts/remove_symbols_to_lowercase.py for one-line summaries."""
    text = str(text).replace("\n", " ").replace("\r", " ")
    text = text.replace("// ", " ").lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    return " ".join(text.split()) or "empty"


def run_command(command, cwd, env):
    print("+", " ".join(map(str, command)), flush=True)
    subprocess.run([str(part) for part in command], cwd=cwd, env=env, check=True)


def encode_texts(texts, name, artifact, work_dir, python, device):
    raw_path = work_dir / f"{name}.txt"
    clean_path = work_dir / f"{name}.clean.txt"
    bpe_path = work_dir / f"{name}.bpe"
    data_dir = work_dir / name
    raw_path.write_text("\n".join(str(text).replace("\n", " ") for text in texts) + "\n",
                        encoding="utf-8")
    clean_path.write_text("\n".join(clean_text(text) for text in texts) + "\n",
                          encoding="utf-8")

    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [str(artifact), str(artifact / "pretraining"), env.get("PYTHONPATH", "")]
    )
    env["TORCH_FORCE_NO_WEIGHTS_ONLY_LOAD"] = "1"
    env["TORCH_HOME"] = str(work_dir / "torch_cache")
    env["MPLCONFIGDIR"] = str(work_dir / "matplotlib")

    run_command(
        [
            artifact / "fastBPE/fast",
            "applybpe",
            bpe_path,
            clean_path,
            artifact / "data/pretrain_data/comments_cleaned.bpe.codes",
        ],
        artifact,
        env,
    )
    data_dir.mkdir(parents=True, exist_ok=True)
    run_command(
        [
            python,
            artifact / "pretraining/fairseq_cli/preprocess.py",
            "--only-source",
            "--testpref",
            bpe_path,
            "--destdir",
            data_dir,
            "--srcdict",
            artifact / "data-bin/my_annotated_dataset/ref_text/dict.txt",
            "--workers",
            "4",
        ],
        artifact,
        env,
    )

    command = [
        python,
        artifact / "scripts/summary_emb.py",
        data_dir,
        "--checkpoint-dir",
        artifact / "checkpoints_pretrained",
        "--checkpoint-file",
        "checkpoint_best.pt",
        "--path",
        artifact / "checkpoints_pretrained/checkpoint_best.pt",
        "--task",
        "summary_embedding",
        "--criterion",
        "masked_permutation_cross_entropy",
        "--gen-subset",
        "test",
        "--results-path",
        work_dir / f"{name}.log",
        "--evaluation-file",
        work_dir / f"{name}.log",
    ]
    if device == "cpu":
        command.append("--cpu")
    run_command(command, artifact, env)

    embedding_path = (
        artifact / "data/my_annotated_dataset_embeddings" / f"{name}_cls_emb.pkl"
    )
    with embedding_path.open("rb") as handle:
        embeddings = np.asarray(pickle.load(handle), dtype=np.float32)
    if len(embeddings) != len(texts):
        raise ValueError(f"SimLLM encoded {len(embeddings)} {name} rows; expected {len(texts)}")
    return embeddings


def artifact_scores(records, level, args, reference_embeddings=None):
    artifact = args.artifact_dir.resolve()
    required = [
        artifact / "checkpoints_pretrained/checkpoint_best.pt",
        artifact / "fastBPE/fast",
        artifact / "data/pretrain_data/comments_cleaned.bpe.codes",
    ]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("Missing SimLLM artifact files: " + ", ".join(missing))
    work_dir = (args.exchange_dir / "artifact_work").resolve()
    work_dir.mkdir(parents=True, exist_ok=True)
    candidates = encode_texts(
        [record["summary"] for record in records],
        f"L{level}_candidate",
        artifact,
        work_dir,
        args.python,
        args.device,
    )
    references = reference_embeddings
    if references is None:
        references = encode_texts(
            [record["reference"] for record in records],
            "shared_reference",
            artifact,
            work_dir,
            args.python,
            args.device,
        )
    denominator = np.linalg.norm(candidates, axis=1) * np.linalg.norm(references, axis=1)
    scores = np.sum(candidates * references, axis=1) / np.maximum(denominator, 1e-12)
    return scores, references


def main():
    parser = argparse.ArgumentParser()
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--prepare", action="store_true")
    mode.add_argument("--import-scores", action="store_true")
    mode.add_argument("--run-artifact", action="store_true")
    parser.add_argument("--input-dir", type=Path, default=Path("BERTScore"))
    parser.add_argument("--input-prefix", default="BERTScore")
    parser.add_argument("--sample-file", type=Path, default=Path("human_eval_target_500.json"))
    parser.add_argument("--exchange-dir", type=Path, default=Path("RQ1/SimLLM/exchange"))
    parser.add_argument("--output-dir", type=Path, default=Path("RQ1/SimLLM"))
    parser.add_argument("--artifact-dir", type=Path, default=Path("SimLLM/SimLLM"))
    parser.add_argument("--python", default=sys.executable)
    parser.add_argument("--device", choices=("cuda", "cpu"), default="cuda")
    parser.add_argument("--levels", type=int, nargs="+", default=list(LEVELS))
    args = parser.parse_args()

    selected_ids = subset_ids(args.sample_file)
    args.exchange_dir.mkdir(parents=True, exist_ok=True)
    means = {}
    reference_embeddings = None
    shared_references = None
    for level in args.levels:
        records = load_level_records(args.input_dir, args.input_prefix, level, selected_ids)
        current_references = [record["reference"] for record in records]
        if shared_references is None:
            shared_references = current_references
        elif args.run_artifact and current_references != shared_references:
            raise ValueError(f"L{level} references differ from the first selected level")
        input_path = args.exchange_dir / f"SimLLM_L{level}_input.jsonl"
        score_path = args.exchange_dir / f"SimLLM_L{level}_scores.txt"
        if args.prepare:
            with input_path.open("w", encoding="utf-8") as handle:
                for record in records:
                    handle.write(
                        json.dumps(
                            {
                                "sample_id": record["sample_id"],
                                "candidate": record["summary"],
                                "reference": record["reference"],
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )
            print(f"Wrote {input_path}")
            continue

        if args.run_artifact:
            scores, reference_embeddings = artifact_scores(
                records, level, args, reference_embeddings
            )
            scores = scores.tolist()
            score_path.write_text(
                "".join(f"{score:.10f}\n" for score in scores), encoding="utf-8"
            )
            print(f"Wrote {score_path}")
        elif not score_path.exists():
            raise FileNotFoundError(
                f"Missing {score_path}; run the official SimLLM artifact on {input_path}"
            )
        if not args.run_artifact:
            with score_path.open("r", encoding="utf-8") as handle:
                scores = [float(line.strip()) for line in handle if line.strip()]
        if len(scores) != len(records):
            raise ValueError(
                f"{score_path} contains {len(scores)} scores; expected {len(records)}"
            )
        means[level] = sum(scores) / len(scores)
        path = save_level_scores(args.output_dir, "SimLLM", level, records, "simllm", scores)
        print(f"L{level}: mean={means[level]:.6f}; wrote {path}")

    if (args.import_scores or args.run_artifact) and set(args.levels) == set(LEVELS):
        print(save_summary(args.output_dir, "SimLLM", "simllm", means, len(selected_ids)))
    elif args.import_scores or args.run_artifact:
        print("Subset complete; run all L1-L9 to write SimLLM_summary.json")


if __name__ == "__main__":
    main()

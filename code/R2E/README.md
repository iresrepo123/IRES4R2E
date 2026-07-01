# R2E

This directory contains the core pipeline for R2E framework.

## Contents

- `query_context2.sc`: Joern query used to extract project context.
- `projects_json_context/`: extracted method and project-context records.
- `sample_dataset.py`: reproducible balanced sampling with seed 42.
- `prompt.md` and `prompt_generator.py`: C1-C9 prompt specification and generation.
- `summary_generator.py`: summary generation through an OpenAI-compatible API.
- `bm25.py`: project-local retrieval of three reconstruction examples.
- `code_generator.py`: summary-to-code reconstruction.
- `cal_distance/cal_distance_IRES.py`: *IRES* calculation with code embeddings.
- `cal_distance/calculate_*.py`: reference-based baseline metrics.
- `annotation_app/`: browser-based human annotation interface.

## Installation

```bash
cd code1
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export SILICONFLOW_API_KEY="your-own-key"
```

Never store an API key in source files or commit a local `.env` file.

## Core pipeline

Run the following commands from the repository root. Script defaults resolve relative to `code1`; explicit paths below make every pipeline connection clear.

```bash
python code1/sample_dataset.py
python code1/prompt_generator.py

python code1/summary_generator.py \
  --input-file code1/promptsv1/L6v2.json \
  --output-file code1/summaries/L6.json \
  --model Pro/deepseek-ai/DeepSeek-V3

python code1/bm25.py \
  --top-k 3 \
  --output code1/bm25_retrieval_database.json

python code1/code_generator.py \
  --input-file code1/summaries/L6.json \
  --output-file code1/reconstructions/L6.json \
  --rag-file code1/bm25_retrieval_database.json \
  --context-file code1/dataset.json \
  --prompt-file code1/prompt.md \
  --top-k 3 \
  --model Qwen/Qwen3-Coder-30B-A3B-Instruct

python code1/cal_distance/cal_distance_IRES.py \
  --input-file code1/reconstructions/L6.json \
  --source-file code1/dataset.json \
  --output-file code1/ires/L6.json \
  --model Qwen/Qwen3-Embedding-8B
```

Repeat summary generation, reconstruction, and *IRES* calculation for each desired context configuration  and model setting, changing the explicit input and output paths.

## Optional baselines

The baseline scripts under `cal_distance/` cover BLEU-4, ROUGE-L, METEOR, BERTScore, Sentence-BERT, USE, BLEURT, InferSent, SIDE, and SimLLM. BLEURT, InferSent, SIDE, and SimLLM require their respective external repositories or model checkpoints; model weights are not included.

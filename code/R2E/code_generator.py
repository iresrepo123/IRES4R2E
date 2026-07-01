import argparse
import json
import os
import time
import requests
import re
import random
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock, local
from requests.adapters import HTTPAdapter

           
try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

                                             

                         
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_SUMMARY_FILE = os.path.join(SCRIPT_DIR, "summaries", "L6.json")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "reconstructions", "L6.json")

      
RAG_FILE = os.path.join(SCRIPT_DIR, "bm25_retrieval_database.json")
CONTEXT_FILE = os.path.join(SCRIPT_DIR, "dataset.json")
PROMPT_FILE = os.path.join(SCRIPT_DIR, "prompt.md")

                                                   
SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "")
API_KEY = f"Bearer {SILICONFLOW_API_KEY}" if SILICONFLOW_API_KEY else ""
API_URL = "https://api.siliconflow.cn/v1/chat/completions"
MODEL_NAME = "Qwen/Qwen3-Coder-30B-A3B-Instruct"

         
MAX_WORKERS = 50
CONNECT_TIMEOUT_SEC = 15
READ_TIMEOUT_SEC = 180
MAX_RETRIES = 6
RETRY_BASE_DELAY_SEC = 2.0
SAVE_INTERVAL = 10 

                                                        

def load_reconstruction_prompt(prompt_file):
    heading = "## Reconstruction Prompt"
    with open(prompt_file, "r", encoding="utf-8") as file:
        text = file.read()

    start = text.find(heading)
    if start == -1:
        raise ValueError(f"Missing '{heading}' section in {prompt_file}")

    section = text[start + len(heading):]
    next_heading = section.find("\n## ")
    if next_heading != -1:
        section = section[:next_heading]

    template = section.strip()
    required = {"{examples_text}", "{signature}", "{summary}"}
    missing = sorted(placeholder for placeholder in required if placeholder not in template)
    if missing:
        raise ValueError(
            f"Missing reconstruction placeholders in {prompt_file}: {missing}"
        )
    return template


def construct_final_prompt(template, signature, summary, examples):
    if examples:
        examples_text = "\n\n".join(
            f"Example {index}:\n{code}"
            for index, code in enumerate(examples, start=1)
        )
    else:
        examples_text = "(No examples available.)"

    replacements = {
        "{examples_text}": examples_text,
        "{signature}": signature,
        "{summary}": summary,
    }
    prompt = template
    for placeholder, value in replacements.items():
        prompt = prompt.replace(placeholder, str(value))
    return prompt

                                                    

def create_robust_session():
    session = requests.Session()
                                                                          
    session.trust_env = False
                                                                               
                                                                         
    adapter = HTTPAdapter(max_retries=0, pool_connections=2, pool_maxsize=2)
    session.mount("https://", adapter)
    session.mount("http://", adapter)
    session.headers.update({
        "Authorization": API_KEY, "Content-Type": "application/json"
    })
    return session

thread_local = local()
file_lock = Lock()

def get_api_session():
    """Use one session per worker; requests.Session is not shared across threads."""
    if not hasattr(thread_local, "api_session"):
        thread_local.api_session = create_robust_session()
    return thread_local.api_session

def retry_delay(attempt, response=None):
    """Use Retry-After when available; otherwise apply jittered exponential backoff."""
    if response is not None:
        retry_after = response.headers.get("Retry-After")
        try:
            if retry_after is not None:
                return max(0.0, float(retry_after))
        except ValueError:
            pass
    upper = min(60.0, RETRY_BASE_DELAY_SEC * (2 ** attempt))
    return upper + random.uniform(0.0, min(5.0, upper / 2))

                                             

def clean_code_markdown(text):
    if not text: return ""
                    
    pattern = r"```(?:java)?\s*(.*?)\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if match: return match.group(1).strip()
    return text.strip()

def load_json_file(filepath, desc="File"):
    print(f"[*] Loading {desc}: {filepath}...")
    if not os.path.exists(filepath):
        print(f"❌ {desc} not found: {filepath}")
        return None
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"❌ Error loading {filepath}: {e}")
        return None

def load_data_maps(rag_data, context_data, top_k=None):
    """
    Build mappings from sample IDs to BM25 examples and function names to signatures.
    """
    rag_map = {}
    if rag_data:
        for item in rag_data:
            if item.get('sample_id') is not None:
                examples = item.get('bm25_topk', item.get('bm25_top3', []))
                rag_map[item['sample_id']] = examples[:top_k] if top_k is not None else examples
    
                                            
    meta_map = {}
    if context_data:
        for item in context_data:
            fname = item.get('func_name')
            sample_id = item.get('sample_id')
            metadata = {
                "sample_id": sample_id,
                "signature": item.get('method_signature')
            }
            if sample_id is not None:
                meta_map[f"id:{sample_id}"] = metadata
            if fname:
                meta_map.setdefault(f"func:{fname}", metadata)
    return rag_map, meta_map

def save_intermediate_results(results):
    with file_lock:
        try:
            with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
                json.dump(results, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"⚠️ Save failed: {e}")

def load_existing_results(filepath):
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, "r", encoding="utf-8") as handle:
            records = json.load(handle)
        if not isinstance(records, list):
            raise ValueError("output root is not a list")
        return {
            str(record["sample_id"]): record
            for record in records
            if record.get("sample_id") is not None
        }
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Cannot resume from {filepath}: {exc}") from exc

                                               

def process_single_item(item, rag_map, meta_map, prompt_template):
    func_name = item.get('func_name')
    summary = item.get('generated_summary') or item.get('summary')
    level = item.get('level', 'unknown')
    
    output_record = {
        "func_name": func_name,
        "sample_id": None,
        "level": level,
        "original_summary": summary,
        "reconstructed_code": None,
        "status": "pending"
    }

    if not summary or not func_name:
        output_record["status"] = "missing_info"
        return output_record

                                      
    sample_id = item.get("sample_id")
    meta = (
        meta_map.get(f"id:{sample_id}")
        if sample_id is not None
        else meta_map.get(f"func:{func_name}")
    )
    if not meta:
                                     
        signature = f"void {func_name}()"
    else:
        signature = meta["signature"]
        if sample_id is None:
            sample_id = meta["sample_id"]
    
    output_record["sample_id"] = sample_id

               
    similar_examples = []
    if sample_id is not None and sample_id in rag_map:
        similar_examples = rag_map[sample_id]

                                 
    user_prompt = construct_final_prompt(
        prompt_template, signature, summary, similar_examples
    )
    
    messages = [
        {"role": "system", "content": "You are a code reconstruction engine. Output only Java code."},
        {"role": "user", "content": user_prompt}
    ]

                                                           
                                     
    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,
        "max_tokens": 1024, 
        "temperature": 0.2, 
        "top_p": 0.95,
    }

    time.sleep(random.uniform(0.1, 0.5))
    retryable_statuses = {429, 500, 502, 503, 504}
    last_error = None
    for attempt in range(MAX_RETRIES):
        response = None
        try:
            response = get_api_session().post(
                API_URL,
                json=payload,
                timeout=(CONNECT_TIMEOUT_SEC, READ_TIMEOUT_SEC),
            )
            if response.status_code == 200:
                data = response.json()
                if "choices" in data and data["choices"]:
                    raw_content = data["choices"][0]["message"]["content"]
                    output_record["reconstructed_code"] = clean_code_markdown(raw_content)
                    output_record["status"] = "success"
                    return output_record
                last_error = "empty choices in successful response"
            elif response.status_code not in retryable_statuses:
                error_detail = response.text[:500]
                print(f"❌ [API Error] {func_name}: {response.status_code} {error_detail}")
                output_record["status"] = "api_error"
                output_record["error_detail"] = f"HTTP {response.status_code}: {error_detail}"
                return output_record
            else:
                last_error = f"HTTP {response.status_code}: {response.text[:500]}"
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        except requests.exceptions.RequestException as exc:
            last_error = f"{type(exc).__name__}: {exc}"
        except (KeyError, TypeError, ValueError) as exc:
            last_error = f"invalid API response ({type(exc).__name__}): {exc}"

        if attempt < MAX_RETRIES - 1:
            delay = retry_delay(attempt, response)
            print(
                f"⏳ [Retry {attempt + 1}/{MAX_RETRIES}] {func_name}: "
                f"{last_error}; waiting {delay:.1f}s",
                flush=True,
            )
            time.sleep(delay)

    print(f"❓ [Failed after {MAX_RETRIES} attempts] {func_name}: {last_error}")
    output_record["status"] = "error"
    output_record["error_detail"] = last_error

    return output_record

                                            

def main():
    global INPUT_SUMMARY_FILE, OUTPUT_FILE, MAX_WORKERS
    global RAG_FILE, CONTEXT_FILE
    global MODEL_NAME
    global CONNECT_TIMEOUT_SEC, READ_TIMEOUT_SEC, MAX_RETRIES, RETRY_BASE_DELAY_SEC

    parser = argparse.ArgumentParser()
    parser.add_argument("--input-file", default=INPUT_SUMMARY_FILE)
    parser.add_argument("--output-file", default=OUTPUT_FILE)
    parser.add_argument("--rag-file", default=RAG_FILE)
    parser.add_argument("--context-file", default=CONTEXT_FILE)
    parser.add_argument("--prompt-file", default=PROMPT_FILE)
    parser.add_argument("--model", default=MODEL_NAME)
    parser.add_argument(
        "--top-k",
        type=int,
        default=None,
        help="Use only the first k retrieved examples; 0 disables retrieval.",
    )
    parser.add_argument("--workers", type=int, default=MAX_WORKERS)
    parser.add_argument("--connect-timeout", type=int, default=CONNECT_TIMEOUT_SEC)
    parser.add_argument("--read-timeout", type=int, default=READ_TIMEOUT_SEC)
    parser.add_argument("--max-retries", type=int, default=MAX_RETRIES)
    parser.add_argument("--retry-base-delay", type=float, default=RETRY_BASE_DELAY_SEC)
    args = parser.parse_args()

    INPUT_SUMMARY_FILE = args.input_file
    OUTPUT_FILE = args.output_file
    MODEL_NAME = args.model
    RAG_FILE = args.rag_file
    CONTEXT_FILE = args.context_file
    MAX_WORKERS = args.workers
    CONNECT_TIMEOUT_SEC = args.connect_timeout
    READ_TIMEOUT_SEC = args.read_timeout
    MAX_RETRIES = args.max_retries
    RETRY_BASE_DELAY_SEC = args.retry_base_delay

    if MAX_WORKERS < 1 or CONNECT_TIMEOUT_SEC < 1 or READ_TIMEOUT_SEC < 1 or MAX_RETRIES < 1:
        raise ValueError("workers, timeouts, and max-retries must all be at least 1")
    if args.top_k is not None and args.top_k < 0:
        raise ValueError("--top-k must be non-negative")

    if not API_KEY:
        raise RuntimeError("Missing API key. Configure the provider API key before running.")

    os.makedirs(os.path.dirname(OUTPUT_FILE), exist_ok=True)
    prompt_template = load_reconstruction_prompt(args.prompt_file)

    summary_data = load_json_file(INPUT_SUMMARY_FILE, "Summaries")
    rag_data_list = load_json_file(RAG_FILE, "RAG DB")
    context_data_list = load_json_file(CONTEXT_FILE, "Context Bridge")

    if not summary_data: return

    rag_map, meta_map = load_data_maps(rag_data_list, context_data_list, args.top_k)

    existing = load_existing_results(OUTPUT_FILE)
    results_by_id = {
        sample_id: record
        for sample_id, record in existing.items()
        if record.get("status") == "success" and record.get("reconstructed_code")
    }
    pending_items = [
        item for item in summary_data
        if str(item.get("sample_id")) not in results_by_id
    ]
    print(
        f"🚀 Starting Reconstruction: {len(results_by_id)} completed, "
        f"{len(pending_items)} pending; workers={MAX_WORKERS}, "
        f"read_timeout={READ_TIMEOUT_SEC}s, retries={MAX_RETRIES}."
    )
    if not pending_items:
        print("✅ Nothing to do; all input samples already have successful reconstructions.")
        return

    processed_count = 0
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_item = {
            executor.submit(
                process_single_item, item, rag_map, meta_map, prompt_template
            ): item
            for item in pending_items
        }
        
        futures = as_completed(future_to_item)
        if tqdm is not None:
            futures = tqdm(futures, total=len(pending_items), desc="Reconstructing")

        for future in futures:
            processed_count += 1
            try:
                res = future.result()
                results_by_id[str(res["sample_id"])] = res
                if tqdm is None and (
                    processed_count % 10 == 0 or processed_count == len(pending_items)
                ):
                    print(
                        f"[*] Progress: {processed_count}/{len(pending_items)}",
                        flush=True,
                    )
                if processed_count % SAVE_INTERVAL == 0:
                    save_intermediate_results(list(results_by_id.values()))
            except Exception as e:
                print(f"🔥 Error: {e}")

    save_intermediate_results(list(results_by_id.values()))
    print(f"\n✅ All Done! Saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()

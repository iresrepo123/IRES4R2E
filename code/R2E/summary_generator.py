import argparse
import requests
import json
import os
import time
import re
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock

session = requests.Session()
session.trust_env = False


           
try:
    from tqdm import tqdm
except ImportError:
    tqdm = None

                                          

                 
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
INPUT_FILE = os.path.join(SCRIPT_DIR, "promptsv1", "L6v2.json")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "summaries", "L6.json")

SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "")
API_KEY = f"Bearer {SILICONFLOW_API_KEY}" if SILICONFLOW_API_KEY else ""
API_URL = "https://api.siliconflow.cn/v1/chat/completions"

          
MODEL_NAME = "Pro/deepseek-ai/DeepSeek-V3"

           
MAX_WORKERS = 40                            
TIMEOUT_SEC = 180
MAX_RETRIES = 5
SAVE_INTERVAL = 5
                                             

file_lock = Lock()

def clean_json_string(text):
    if not text: return "{}"
    pattern = r"```(?:json)?\s*(.*?)\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if match: return match.group(1)
    
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1: 
        return text[start:end+1]
    return text

def save_intermediate_results(results):
    with file_lock:
        os.makedirs(os.path.dirname(os.path.abspath(OUTPUT_FILE)), exist_ok=True)
        temp_file = f"{OUTPUT_FILE}.tmp"
        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        os.replace(temp_file, OUTPUT_FILE)

def record_key(item):
    """Build the same stable key for prompt rows and generated result rows."""
    if item.get("sample_id") is not None:
        return f"id:{item['sample_id']}|level:{item.get('level', 'unknown')}"
    return f"func:{item.get('func_name', 'unknown')}|level:{item.get('level', 'unknown')}"

def load_existing_results(filepath):
    if not os.path.exists(filepath):
        return {}
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            rows = json.load(f)
        if not isinstance(rows, list):
            raise ValueError("output root is not a JSON array")
        return {record_key(row): row for row in rows}
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Unable to resume from existing output {filepath}: {exc}") from exc

def process_single_item(item):
    func_name = item.get('func_name', 'unknown')
    level = item.get('level', 'unknown')
    system_prompt = item.get('system_prompt', '')
    user_prompt = item.get('user_prompt', '')
    
    output_record = {
        "sample_id": item.get("sample_id"),
        "func_name": func_name,
        "dataset_source_file": item.get("dataset_source_file"),
        "level": level,
        "status": "pending",
        "generated_summary": None, 
        "raw_response": None
    }

    if not user_prompt:
        output_record["status"] = "invalid_input"
        return output_record

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ]

    payload = {
        "model": MODEL_NAME,
        "messages": messages,
        "stream": False,
        "max_tokens": 1024,
        "temperature": 0,
        "top_p": 0.9,
                               
                                                     
    }

    headers = {
        "Authorization": API_KEY,
        "Content-Type": "application/json"
    }

    current_retry = 0
    success = False

                                  
    time.sleep(0.2) 

    while current_retry < MAX_RETRIES and not success:
        try:
            response = session.post(API_URL, json=payload, headers=headers, timeout=TIMEOUT_SEC)
            
            if response.status_code == 200:
                data = response.json()
                if 'choices' in data and len(data['choices']) > 0:
                    raw_content = data['choices'][0]['message']['content']
                    cleaned_json_str = clean_json_string(raw_content)
                    
                    try:
                        parsed_json = json.loads(cleaned_json_str)
                        summary_val = parsed_json.get("summary")

                        if summary_val:
                            output_record["generated_summary"] = summary_val
                            output_record["status"] = "success"
                            success = True
                        else:
                            output_record["status"] = "empty_keys"
                            output_record["raw_response"] = raw_content
                            current_retry += 1

                    except json.JSONDecodeError:
                                             
                                                                
                        output_record["status"] = "json_parse_error"
                        output_record["raw_response"] = raw_content
                        current_retry += 1
                else:
                    current_retry += 1
            
            elif response.status_code == 429:
                             
                print(f"⏳ [429 Limit] {func_name} - Retrying...")
                wait_time = 3 * (2 ** current_retry) 
                time.sleep(wait_time)
                current_retry += 1
            
            else:
                                       
                print(f"❌ [API Error] {func_name}: Status {response.status_code} | Msg: {response.text[:100]}")
                current_retry += 1
                time.sleep(2) 

        except Exception as e:
                    
            print(f"❌ [Net Exception] {func_name}: {e}")
            current_retry += 1
            time.sleep(2 * current_retry)

    if not success and output_record["status"] == "pending":
         output_record["status"] = "failed_network"

    return output_record

def main():
    global INPUT_FILE, OUTPUT_FILE, MODEL_NAME

    parser = argparse.ArgumentParser()
    parser.add_argument("--input-file", default=INPUT_FILE)
    parser.add_argument("--output-file", default=OUTPUT_FILE)
    parser.add_argument("--model", default=MODEL_NAME)
    args = parser.parse_args()

    INPUT_FILE = args.input_file
    OUTPUT_FILE = args.output_file
    MODEL_NAME = args.model

    if not API_KEY:
        raise RuntimeError(
            "Missing SILICONFLOW_API_KEY. Set it in the environment before running."
        )

    if not os.path.exists(INPUT_FILE):
        print(f"❌ Error: input file not found: {INPUT_FILE}")
        return

    print(f"📂 Reading prompts: {INPUT_FILE}")
    print(f"🤖 Model: {MODEL_NAME}")
    
    with open(INPUT_FILE, "r", encoding="utf-8") as f:
        input_data = json.load(f)

    total_count = len(input_data)
    existing = load_existing_results(OUTPUT_FILE)
    results_by_key = {
        key: row
        for key, row in existing.items()
        if row.get("status") == "success" and row.get("generated_summary")
    }
    pending_data = [
        item for item in input_data
        if record_key(item) not in results_by_key
    ]
    reused_count = total_count - len(pending_data)
    print(
        f"🚀 Starting generation (workers: {MAX_WORKERS}): "
        f"completed {reused_count}, pending {len(pending_data)}..."
    )

    def ordered_results():
        return [
            results_by_key[record_key(item)]
            for item in input_data
            if record_key(item) in results_by_key
        ]
    
    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        future_to_item = {
            executor.submit(process_single_item, item): item
            for item in pending_data
        }
        
        done_count = 0
        if tqdm:
            for future in tqdm(
                as_completed(future_to_item), total=len(pending_data)
            ):
                res = future.result()
                results_by_key[record_key(res)] = res
                done_count += 1
                if done_count % SAVE_INTERVAL == 0:
                    save_intermediate_results(ordered_results())
        else:
            for future in as_completed(future_to_item):
                res = future.result()
                results_by_key[record_key(res)] = res
                done_count += 1
                if done_count % 10 == 0: 
                    print(f"Progress: {done_count}/{len(pending_data)}")
                if done_count % SAVE_INTERVAL == 0:
                    save_intermediate_results(ordered_results())

    results = ordered_results()
    save_intermediate_results(results)

    success_count = sum(1 for r in results if r['status'] == 'success')
    print(f"\n📊 Final results: {success_count}/{total_count} succeeded")
    print(f"💾 Results saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()

import argparse
import json
import os
import time
import requests
import numpy as np
import concurrent.futures
import re
import random
try:
    from tqdm import tqdm
except ImportError:
    def tqdm(iterable, **_kwargs):
        return iterable
from collections import Counter
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

                                             

SILICONFLOW_API_KEY = os.getenv("SILICONFLOW_API_KEY", "")
API_KEY = f"Bearer {SILICONFLOW_API_KEY}" if SILICONFLOW_API_KEY else ""
API_URL = "https://api.siliconflow.cn/v1/embeddings"
MODEL_NAME = "Qwen/Qwen3-Embedding-8B"

SCRIPT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
INPUT_GENERATED_FILE = os.path.join(SCRIPT_DIR, "reconstructions", "L6.json")
INPUT_SOURCE_FILE = os.path.join(SCRIPT_DIR, "dataset.json")
OUTPUT_FILE = os.path.join(SCRIPT_DIR, "ires", "L6.json")

MAX_WORKERS = 50
KEEP_SIGNATURE = False

                                               

os.environ.pop("http_proxy", None)
os.environ.pop("https_proxy", None)

def create_resilient_session():
    session = requests.Session()
    retry_strategy = Retry(
        total=5, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"], raise_on_status=False
    )
    adapter = HTTPAdapter(max_retries=retry_strategy, pool_connections=MAX_WORKERS, pool_maxsize=MAX_WORKERS*2)
    session.mount("https://", adapter)
    session.headers.update({"Authorization": API_KEY, "Content-Type": "application/json"})
    return session

api_session = create_resilient_session()

def get_embedding_via_api(text, debug_id=None):
    if not text or len(text.strip()) < 1: 
        return None, "empty_text_after_cleaning"
        
    safe_text = text[:8000] 
    payload = {"model": MODEL_NAME, "input": safe_text, "encoding_format": "float"}
    try:
        response = api_session.post(API_URL, json=payload, timeout=(5, 30))
        if response.status_code == 200:
            data = response.json()
            if 'data' in data and len(data['data']) > 0:
                return data['data'][0]['embedding'], None
            else:
                return None, "api_response_format_error"
        else:
            return None, f"api_error_{response.status_code}"
    except Exception as e:
        return None, f"api_exception_{str(e)}"

                                               

def full_clean_pipeline(raw_code, keep_signature=True):
    if not raw_code: return ""
    code = raw_code
    
                      
    code = re.sub(r'@\w+(\s*\(.*?\))?', '', code, flags=re.DOTALL)
    
              
    code = re.sub(r'/\*[\s\S]*?\*/', '', code)
    
              
    code = re.sub(r'^\s*//.*', '', code, flags=re.MULTILINE)

                
    if not keep_signature:
        start_index = code.find('{')
        end_index = code.rfind('}')
        if start_index != -1 and end_index != -1 and end_index > start_index:
            code = code[start_index+1 : end_index]
        else:
                                                           
                                    
            pass 
    
              
    modifiers = ['public', 'private', 'protected', 'final', 'static', 'synchronized', 'native', 'transient', 'volatile', 'abstract', 'default']
    pattern = r'\b(' + '|'.join(modifiers) + r')\b'
    code = re.sub(pattern, '', code)
    
    code = ' '.join(code.split())
    return code.strip()

                                             

def load_source_map(source_file):
    print(f"[*] Loading targets from {source_file}...")
    id_map = {}
    if not os.path.exists(source_file): return {}
    with open(source_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    for item in data:
        s_id = item.get('sample_id')
        code = item.get('code') or item.get('raw_code') or item.get('method_body')
        if not code:
            sig = item.get('method_signature', '')
            body = item.get('method_body_no_sig', '')
            if sig and body:
                code = f"{sig} {{\n{body}\n}}"
            elif sig:
                code = sig
            elif body:
                code = body
        if s_id is not None and code:
            id_map[str(s_id)] = code
    print(f"    Loaded {len(id_map)} targets into ID Map.")
    return id_map

def cosine_similarity(vec_a, vec_b):
    if vec_a is None or vec_b is None: return 0.0
    a = np.array(vec_a); b = np.array(vec_b)
    norm_a = np.linalg.norm(a); norm_b = np.linalg.norm(b)
    if norm_a == 0 or norm_b == 0: return 0.0
    return float(np.dot(a, b) / (norm_a * norm_b))

def process_aligned_item(gen_item, source_map):
    s_id = gen_item.get('sample_id')
    func_name = gen_item.get('func_name', 'unknown')
    
             
    if s_id is None:
        return {'status': 'fail', 'reason': 'no_id_in_gen', 'id': 'N/A', 'func': func_name}
    
    original_code = source_map.get(str(s_id))
    if not original_code:
        return {'status': 'fail', 'reason': 'source_id_not_found', 'id': s_id, 'func': func_name}

    gen_code = gen_item.get('reconstructed_code')
                                   
    if not gen_code or not gen_code.strip():
        result_item = gen_item.copy()
        result_item['irs_score'] = 0.0
        return {'status': 'success', 'data': result_item}              

           
    clean_orig = full_clean_pipeline(original_code, keep_signature=KEEP_SIGNATURE)
    clean_gen = full_clean_pipeline(gen_code, keep_signature=KEEP_SIGNATURE)
    
                                 
    emb_orig, err_orig = get_embedding_via_api(clean_orig, s_id)
    if emb_orig is None:
                                           
        return {'status': 'fail', 'reason': f'emb_orig_fail:{err_orig}', 'id': s_id, 'func': func_name}
        
                              
    emb_gen, err_gen = get_embedding_via_api(clean_gen, s_id)
    
    if emb_gen is None:
                                               
        if "empty_text" in str(err_gen):
            result_item = gen_item.copy()
            result_item['irs_score'] = 0.0
            return {'status': 'success', 'data': result_item}                
        else:
                               
            return {'status': 'fail', 'reason': f'emb_gen_fail:{err_gen}', 'id': s_id, 'func': func_name}

             
    score = cosine_similarity(emb_orig, emb_gen)
    
    result_item = gen_item.copy()
    result_item['irs_score'] = score
    return {'status': 'success', 'data': result_item}

                                            

def main():
    global INPUT_GENERATED_FILE, INPUT_SOURCE_FILE, OUTPUT_FILE, MODEL_NAME

    parser = argparse.ArgumentParser()
    parser.add_argument("--input-file", default=INPUT_GENERATED_FILE)
    parser.add_argument("--source-file", default=INPUT_SOURCE_FILE)
    parser.add_argument("--output-file", default=OUTPUT_FILE)
    parser.add_argument("--model", default=MODEL_NAME)
    args = parser.parse_args()

    INPUT_GENERATED_FILE = args.input_file
    INPUT_SOURCE_FILE = args.source_file
    OUTPUT_FILE = args.output_file
    MODEL_NAME = args.model

    if not API_KEY:
        raise RuntimeError(
            "Missing SILICONFLOW_API_KEY. Set it in the environment before running."
        )

    source_map = load_source_map(INPUT_SOURCE_FILE)
    if not source_map: return

    if not os.path.exists(INPUT_GENERATED_FILE):
        print(f"❌ Input file not found.")
        return
    with open(INPUT_GENERATED_FILE, 'r', encoding='utf-8') as f:
        gen_data = json.load(f)

    print(f"[*] Processing {len(gen_data)} items...")
    os.makedirs(os.path.dirname(os.path.abspath(OUTPUT_FILE)), exist_ok=True)
    
    final_results = []
    failures = []             
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [executor.submit(process_aligned_item, item, source_map) for item in gen_data]
        
        for future in tqdm(concurrent.futures.as_completed(futures), total=len(gen_data)):
            res = future.result()
            if res['status'] == 'success':
                final_results.append(res['data'])
            else:
                failures.append(res)       

            
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        json.dump(final_results, f, indent=2, ensure_ascii=False)
        
    scores = [r['irs_score'] for r in final_results]
    
    print("\n" + "="*50)
    print(f"✅ Success: {len(final_results)} items. Avg IRS: {np.mean(scores):.4f}")
    print(f"❌ Failed:  {len(failures)} items.")
    print("="*50)
    
                 
    if failures:
        print("\n[Failure Analysis]")
        reason_counter = Counter([f['reason'] for f in failures])
        for reason, count in reason_counter.most_common():
            print(f"  - {reason}: {count} cases")
            
        print("\n[Detailed Failure Log (First 15)]")
        for i, fail in enumerate(failures[:15]):
            print(f"  {i+1}. ID: {fail['id']} | Func: {fail['func']}")
            print(f"     Reason: {fail['reason']}")
            if 'code_snippet' in fail:
                print(f"     Snippet: {fail['code_snippet']}...")                
            print("-" * 30)

if __name__ == "__main__":
    main()

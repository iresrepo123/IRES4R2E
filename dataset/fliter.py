import json
import os
import re
import hashlib

                                          
INPUT_DIR = "selected_projects_json"         
OUTPUT_DIR = "cleaned_projectsv2_json_addv3"         
                                             

def remove_comments_and_strings(source):
    pattern = re.compile(
        r'//.*?$|/\*.*?\*/|\'(?:\\.|[^\\\'])*\'|"(?:\\.|[^\\"])*"',
        re.DOTALL | re.MULTILINE
    )
    return re.sub(pattern, ' ', source)

def get_function_body(code):
    start_index = code.find('{')
    if start_index == -1:
        return None
    end_index = code.rfind('}')
    if end_index == -1 or end_index <= start_index:
        return None
    return code[start_index+1:end_index]

def is_valid_method(method_json):
    code = method_json.get('original_string', '')
    if not code:
        return False, "missing_code"
    
    func_name = method_json.get('func_name', '').lower()
    docstring = method_json.get('docstring', '').lower()

               
    if 'test' in func_name:
        return False, "is_test_code"
    
                 
    if 'generated' in docstring:
        return False, "is_generated_code"

               
    body = get_function_body(code)
    if body is None:
        return False, "abstract_no_body"

               
    if not body.strip():
        return False, "empty_body"

               
    clean_body = remove_comments_and_strings(body)
    statement_count = clean_body.count(';')
    
    if statement_count < 2:
        return False, f"fewer_statements ({statement_count})"

    return True, "pass"

def clean_dataset():
    if not os.path.exists(INPUT_DIR):
        print(f"❌ Input directory not found: '{INPUT_DIR}'")
        return

    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        print(f"📂 Created output directory: '{OUTPUT_DIR}'")

                      
    seen_hashes = set()                    
    seen_func_names = set()             

    global_stats = {
        "total": 0,
        "kept": 0,
        "duplicate_content": 0,       
        "duplicate_name": 0,                   
        "abstract_no_body": 0,
        "is_test_code": 0,      
        "is_generated_code": 0,
        "empty_body": 0,
        "fewer_statements": 0,
        "other_errors": 0
    }

    files = [f for f in os.listdir(INPUT_DIR) if f.endswith('.json')]
    
    for filename in files:
        input_path = os.path.join(INPUT_DIR, filename)
        output_path = os.path.join(OUTPUT_DIR, filename)
        
        print(f"\nProcessing {filename}...")
        
        try:
            with open(input_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
        except Exception as e:
            print(f"  ❌ Failed to read file: {e}")
            continue

        cleaned_data = []
        
        for item in data:
            global_stats["total"] += 1
            
                    
            code_content = item.get('original_string', '')
            func_name = item.get('func_name', '')                                 

            if not code_content or not func_name:
                global_stats["other_errors"] += 1
                continue

                                                       
                                  
                                                                 
            if func_name in seen_func_names:
                global_stats["duplicate_name"] += 1
                continue 
            
                                                           
                                         
            code_hash = hashlib.md5(code_content.encode('utf-8')).hexdigest()
            if code_hash in seen_hashes:
                global_stats["duplicate_content"] += 1
                continue 
            
                                                  
            is_valid, reason = is_valid_method(item)
            
            if is_valid:
                cleaned_data.append(item)
                                                
                seen_func_names.add(func_name)
                seen_hashes.add(code_hash)
                global_stats["kept"] += 1
            else:
                        
                if reason.startswith("fewer_statements"):
                    global_stats["fewer_statements"] += 1
                elif reason == "abstract_no_body":
                    global_stats["abstract_no_body"] += 1
                elif reason == "empty_body":
                    global_stats["empty_body"] += 1
                elif reason == "is_test_code":       
                    global_stats["is_test_code"] += 1
                elif reason == "is_generated_code":    
                    global_stats["is_generated_code"] += 1
                else:
                    global_stats["other_errors"] += 1

                  
        if cleaned_data:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(cleaned_data, f, indent=4, ensure_ascii=False)
        
        print(f"  -> Original: {len(data)} records | Cleaned: {len(cleaned_data)} records")

                    
    print("\n" + "="*40)
    print("📊 Final Dataset Cleaning Report")
    print("="*40)
    print(f"📥 Total input records: {global_stats['total']}")
    print("-" * 40)
    print(f"🗑️  Duplicate function names removed: {global_stats['duplicate_name']}")
    print(f"🗑️  Duplicate code records removed: {global_stats['duplicate_content']}")
    print(f"🗑️  Abstract or bodyless methods removed: {global_stats['abstract_no_body']}")
    print(f"🗑️  Empty methods removed: {global_stats['empty_body']}")
    print(f"🗑️  Simple methods removed (<2 statements): {global_stats['fewer_statements']}")
    print(f"🗑️  Test methods removed: {global_stats['is_test_code']}")
    print(f"🗑️  Generated methods removed: {global_stats['is_generated_code']}")
    print("-" * 40)
    print(f"✅ Records kept: {global_stats['kept']}")
    print(f"📂 Results saved to: {OUTPUT_DIR}/")
    print("="*40)

if __name__ == "__main__":
    clean_dataset()

import json
import os
from collections import defaultdict

def main():
                                              
                      
    INPUT_FILE = "./my_java_data.json"
    
          
    OUTPUT_DIR = "./selected_projects_json"
    
             
    MERGED_FILENAME = "all_selected_14_projects.json"

                  
    TARGET_REPOS = [
        "Unidata/thredds",
        "alkacon/opencms-core",
        "apache/flink",
        "apache/groovy",
        "cdk/cdk",
        "deeplearning4j/deeplearning4j",
        "elki-project/elki",
        "facebookarchive/hadoop-20",
        "google/error-prone-javac",
        "google/j2objc",
        "hazelcast/hazelcast",
        "lessthanoptimal/BoofCV",
        "looly/hutool",
        "zaproxy/zaproxy"
    ]
                                                 

    if not os.path.exists(INPUT_FILE):
        print(f"❌ Input file not found: {INPUT_FILE}")
        return

             
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)

    print(f"🔄 Reading source file: {INPUT_FILE} ...")
    
                                         
    project_buckets = defaultdict(list)
              
    all_merged_data = []
    
                   
    target_set = set(TARGET_REPOS)

                       
    try:
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                
                           
                item = json.loads(line)
                repo_name = item.get('repo')
                
                         
                if repo_name in target_set:
                               
                    project_buckets[repo_name].append(item)
                              
                    all_merged_data.append(item)
                    
                                     
                if line_num % 100000 == 0:
                    print(f"   ... Processed {line_num} lines ...")

    except Exception as e:
        print(f"❌ Read error: {e}")
        return

    print(f"✅ Filtering complete. Extracted {len(all_merged_data)} target records.")
    print("-" * 60)

                                          
    print("💾 Saving individual project files...")
    
    if not project_buckets:
        print("⚠️ No target projects matched. Check the names in TARGET_REPOS.")
    
    for repo_name, items in project_buckets.items():
                        
        safe_filename = repo_name.replace("/", "_") + ".json"
        file_path = os.path.join(OUTPUT_DIR, safe_filename)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(items, f, ensure_ascii=False, indent=4)
        
        print(f"   -> [{len(items):<5}] {safe_filename}")

               
    if all_merged_data:
        print("-" * 60)
        print(f"💾 Saving merged file with {len(all_merged_data)} records...")
        merged_path = os.path.join(OUTPUT_DIR, MERGED_FILENAME)
        
        with open(merged_path, 'w', encoding='utf-8') as f:
            json.dump(all_merged_data, f, ensure_ascii=False, indent=4)
        print(f"   -> {MERGED_FILENAME}")
    
    print("\n" + "="*60)
    print("🎉 Complete.")
    print(f"📂 Filtered JSON files saved to: {os.path.abspath(OUTPUT_DIR)}")
    print("="*60)

if __name__ == "__main__":
    main()

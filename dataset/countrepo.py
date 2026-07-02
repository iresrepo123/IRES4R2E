import json
import os
from collections import Counter

                                                   
INPUT_FILE = "./my_java_data.json"
TOP_N = 50
                                             

def main():
    if not os.path.exists(INPUT_FILE):
        print(f"❌ File not found: {INPUT_FILE}")
        print("💡 Make sure the export script has run and produced my_java_data.json.")
        return

    print(f"🔄 Reading {INPUT_FILE} ...")
    
    data_list = []
    try:
                                                                     
        with open(INPUT_FILE, 'r', encoding='utf-8') as f:
            for line_num, line in enumerate(f, 1):
                line = line.strip()
                if not line:
                    continue
                try:
                                                                    
                    item = json.loads(line)
                    data_list.append(item)
                except json.JSONDecodeError as e:
                    print(f"⚠️ Could not parse line {line_num}; skipping it. Error: {e}")

        if not data_list:
            print("The dataset is empty. Check the input file.")
            return

        print(f"📊 Loaded {len(data_list)} function samples.")
        print("-" * 50)

                                      
                                                                          
        repos = [item.get('repo', 'UNKNOWN_REPO') for item in data_list]

                                
        repo_counts = Counter(repos)

                                                        
                                                                  
        sorted_repos = repo_counts.most_common(TOP_N)

                                     
        print(f"{'Rank':<5} | {'Count':<8} | {'Repository Name'}")
        print("-" * 60)

        for rank, (repo_name, count) in enumerate(sorted_repos, 1):
                                                               
            print(f"{rank:<5} | {count:<8} | {repo_name}")

        print("-" * 60)
        print(f"✅ Complete. Found {len(repo_counts)} distinct repositories.")

    except Exception as e:
        print(f"❌ Unexpected error: {e}")

if __name__ == "__main__":
    main()

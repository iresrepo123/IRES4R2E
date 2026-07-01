import argparse
import json
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
DEFAULT_INPUT_FILE = SCRIPT_DIR / "dataset.json"
DEFAULT_OUTPUT_DIR = SCRIPT_DIR / "promptsv1"
DEFAULT_PROMPT_FILE = SCRIPT_DIR / "prompt.md"
TEMPLATE_PLACEHOLDERS = {
    "{signature}",
    "{body}",
    "{class_name}",
    "{file_path}",
    "{field_list}",
    "{class_fields}",
    "{sibling_methods}",
    "{callees}",
    "{callers}",
}

                                                                       

def load_prompt_templates(prompt_file):
    """Load the common and L1-L9 prompts from the canonical Markdown file."""
    sections = {}
    current_heading = None
    current_lines = []

    with prompt_file.open("r", encoding="utf-8") as file:
        for line in file:
            if line.startswith("## "):
                if current_heading is not None:
                    sections[current_heading] = "".join(current_lines).strip()
                current_heading = line[3:].strip().rstrip("：:")
                current_lines = []
            elif current_heading is not None:
                current_lines.append(line)

    if current_heading is not None:
        sections[current_heading] = "".join(current_lines).strip()

    required = ["Common Prompt"] + [f"L{level} Prompt" for level in range(1, 10)]
    missing = [heading for heading in required if not sections.get(heading)]
    if missing:
        raise ValueError(
            f"Missing prompt sections in {prompt_file}: {', '.join(missing)}"
        )

    return (
        sections["Common Prompt"],
        {
            f"L{level}": sections[f"L{level} Prompt"]
            for level in range(1, 10)
        },
    )


                                                 

def format_context_list_detailed(sub_list, max_items=10):

    if not sub_list: return "(None)"
    formatted = []
    
           
    valid_list = [item for item in sub_list if isinstance(item, dict)]
    
    for item in valid_list[:max_items]:
                 
        sig = item.get('signature') or item.get('method_signature') or item.get('name') or 'unknown'
        
                        
        path = item.get('file_path') or "(Unknown File)"
        
                                 
        entry = f"- Signature: {sig}\n  File Path: {path}"
        formatted.append(entry)
        
    if len(valid_list) > max_items: 
        formatted.append(f"... ({len(valid_list) - max_items} others omitted)")
        
    return "\n".join(formatted) if formatted else "(None)"


def format_simple_list(sub_list, max_items=8):

    if not sub_list: return "(None)"
    formatted = []
    valid_list = [item for item in sub_list if isinstance(item, dict) or isinstance(item, str)]
    
    for item in valid_list[:max_items]:
        if isinstance(item, dict):
            sig = item.get('signature') or item.get('method_signature') or item.get('name') or 'unknown'
        else:
            sig = str(item)
        formatted.append(f"- {sig}")
        
    if len(valid_list) > max_items:
        formatted.append(f"... ({len(valid_list) - max_items} others omitted)")
        
    return "\n".join(formatted)

def safe_replace(template, placeholders):
    s = template
    for key, val in placeholders.items():
        s = s.replace(key, str(val))
    return s

                                           

def parse_args():
    parser = argparse.ArgumentParser(description="Generate L1-L9 summary prompts.")
    parser.add_argument(
        "--prompt-file",
        type=Path,
        default=DEFAULT_PROMPT_FILE,
        help=f"Markdown prompt specification (default: {DEFAULT_PROMPT_FILE})",
    )
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT_FILE,
        help=f"Input dataset (default: {DEFAULT_INPUT_FILE})",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})",
    )
    return parser.parse_args()


def main():
    args = parse_args()
    if not args.input.is_file():
        raise FileNotFoundError(f"Input file not found: {args.input}")
    if not args.prompt_file.is_file():
        raise FileNotFoundError(f"Prompt file not found: {args.prompt_file}")

    common_system_instruction, user_templates = load_prompt_templates(args.prompt_file)

            
    args.output_dir.mkdir(parents=True, exist_ok=True)

    print(f"[*] Reading input file: {args.input}")
    with args.input.open('r', encoding='utf-8') as f:
        data = json.load(f)
    if not isinstance(data, list):
        raise ValueError("Input file must contain a JSON array")
    
    print(f"[*] Processing {len(data)} items...")
    
    prompts_by_level = {
        "L1": [], "L2": [], "L3": [], 
        "L4": [], "L5": [], "L6": [], 
        "L7": [], "L8": [], "L9": []
    }

    for idx, item in enumerate(data):
              
        func_name = item.get('func_name', 'unknown')
        sample_id = item.get('sample_id', idx)
        dataset_source_file = item.get('dataset_source_file', 'unknown')
        signature = item.get('method_signature', '') or f"Method: {func_name}"
        body = item.get('method_body_no_sig', '') or item.get('code', '') or "(Body empty)"
        class_name = item.get('class_name', 'Unknown')
        file_path = item.get('file_path', 'Unknown')
        fields_list = item.get('class_fields', [])
        fields_str = ", ".join(fields_list[:10]) if fields_list else "(No fields)"
        
                                     
        
                           
        siblings_list = item.get('sibling_methods', [])
        siblings_str = format_simple_list(siblings_list)

                                             
        callees_list = item.get('callees', [])
        callees_str = format_context_list_detailed(callees_list)
        
                                             
        callers_list = item.get('callers', [])
        callers_str = format_context_list_detailed(callers_list)

        replacements = {
            "{signature}": signature,
            "{body}": body,
            "{class_name}": class_name,
            "{file_path}": file_path,
            "{field_list}": fields_str,
            "{class_fields}": fields_str,
            "{sibling_methods}": siblings_str,
            "{callees}": callees_str,
            "{callers}": callers_str
        }

                      
        level_map = list(user_templates.items())

        for level_key, template in level_map:
            user_prompt = safe_replace(template, replacements)
            unresolved = [
                placeholder
                for placeholder in TEMPLATE_PLACEHOLDERS
                if placeholder in user_prompt
            ]
            if unresolved:
                raise ValueError(
                    f"Unresolved placeholders for sample {sample_id}, "
                    f"{level_key}: {sorted(set(unresolved))}"
                )
            
            prompt_entry = {
                "sample_id": sample_id,
                "func_name": func_name,
                "dataset_source_file": dataset_source_file,
                "level": level_key,
                "system_prompt": common_system_instruction,
                "user_prompt": user_prompt
            }
            prompts_by_level[level_key].append(prompt_entry)

        
    print(f"[*] Saving files to {args.output_dir}/ ...")
    for level_key, prompts in prompts_by_level.items():
        if len(prompts) != len(data):
            raise ValueError(
                f"{level_key} contains {len(prompts)} prompts; expected {len(data)}"
            )
        filename = f"{level_key}v2.json"
        filepath = args.output_dir / filename
        with filepath.open('w', encoding='utf-8') as f:
            json.dump(prompts, f, indent=2, ensure_ascii=False)
        print(f"   - {filename}: {len(prompts)} records")

    print("✅ All done!")

if __name__ == "__main__":
    main()

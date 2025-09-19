import os
import json
import re

def extract_contract_source(text, contract_name):
    if text.find("```")!=-1:
        text = text[text.find("```"):]
    pattern = rf'\bcontract\s+{re.escape(contract_name)}\b(?!.*\bstrictly\b)'
    match = re.search(pattern, text, re.IGNORECASE)
    if not match: return ""
    start_idx = match.start()
    
    brace_pos = text.find('{', start_idx)
    if brace_pos == -1:
        return ""
    
    brace_count = 1
    current_pos = brace_pos + 1
    length = len(text)
    
    while current_pos < length and brace_count > 0:
        if text[current_pos] == '{':
            brace_count += 1
        elif text[current_pos] == '}':
            brace_count -= 1
        current_pos += 1
    
    if brace_count != 0:
        return ""
    end_idx = current_pos
    contract_source = text[start_idx:end_idx]
    
    return contract_source

def concatenate(input_path, model_name):
    prompt_path = "../dataset/prompt"
    code_path = "../dataset/source_code"
    combined_path = "../results/generated_contract"
    model_path = os.path.join(input_path, model_name)
    os.makedirs(os.path.join(combined_path, model_name), exist_ok=True)

    total_sum = 0
    success_sum = 0
    for contract_folder in os.listdir(model_path):
        combined_contract_path = os.path.join(combined_path, model_name, contract_folder)
        os.makedirs(combined_contract_path, exist_ok=True)
        for output_file in os.listdir(os.path.join(model_path, contract_folder)):
            if not output_file.endswith("txt"): continue
            address = contract_folder

            total_sum += 1
            prompt_file = os.path.join(prompt_path, address + ".json")
            total_contract_file = os.path.join(code_path, address + ".sol")
            answer_file = os.path.join(model_path, contract_folder, output_file)
            combine_file = os.path.join(combined_contract_path, os.path.splitext(output_file)[0]+".sol")

            with open(answer_file, "r") as f: response = f.read()
            with open(prompt_file, "r") as f: prompt = json.load(f)
            with open(total_contract_file, "r") as f: source_code = f.read()

            if os.path.exists(combine_file): os.remove(combine_file)
            response_code = extract_contract_source(response, prompt["contract_name"])
            ground_truth = prompt["ground_truth"]

            if len(response_code) > 5:
                if source_code.find(ground_truth) != -1:
                    new_code = source_code.replace(ground_truth, response_code)
                    with open(combine_file, "w") as f: f.write(new_code)
                    success_sum += 1
    return total_sum, success_sum
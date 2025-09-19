import os
import re
import json
from slither import Slither
from slither.core.declarations import Contract, Function
from typing import Set, List
import subprocess
import random

function_pattern = re.compile(
    r'function\s+([\w]+)\s*\(([^)]*)\)\s*([\w\s()]*)\s*(?:returns\s*\(([^)]*)\))?\s*({(?:[^{}]|{(?:[^{}]|{(?:[^{}]|{[^{}]*})*})*})*})',
    re.DOTALL
)

def get_comment_ranges(text):
    comment_ranges = []
    pattern = r'//.*?$|/\*[\s\S]*?\*/'
    for match in re.finditer(pattern, text, flags=re.MULTILINE):
        comment_ranges.append((match.start(), match.end()))
    return comment_ranges

def is_in_ranges(pos, ranges):
    for start, end in ranges:
        if start <= pos < end:
            return True
    return False

def extract_blocks(text):
    comment_ranges = get_comment_ranges(text)
    blocks = []
    pos = 0
    length = len(text)
    
    while pos < length:
        if is_in_ranges(pos, comment_ranges):
            for s, e in comment_ranges:
                if s <= pos < e:
                    pos = e
                    break
            continue
        
        match = re.search(r'\b(contract|interface|library|abstract)\s+\w+', text[pos:], re.IGNORECASE)
        if not match:
            break
        start = pos + match.start()
        if is_in_ranges(start, comment_ranges):
            pos = start + 1
            continue
        brace_pos = text.find('{', start)
        if brace_pos == -1:
            break
        
        brace_count = 1
        current_pos = brace_pos + 1
        while current_pos < length and brace_count > 0:
            if text[current_pos] == '{':
                brace_count += 1
            elif text[current_pos] == '}':
                brace_count -= 1
            current_pos += 1
        end = current_pos
        blocks.append((start, end))
        pos = end
    return blocks

def extract_comments_above_blocks(text, blocks):
    comment_ranges = get_comment_ranges(text)
    block_comments = []
    
    for i, (start, end) in enumerate(blocks):
        comment_start = start
        while comment_start > 0:
            if text[comment_start - 1] == '\n':
                break
            comment_start -= 1
        
        if i == 0:
            comments = []
            for s, e in comment_ranges:
                if e <= comment_start:
                    comments.append(text[s:e])
            merged_comments = '\n'.join(comments)
            block_comments.append(merged_comments.strip())
            continue
        
        prev_block_end = blocks[i - 1][1]
        comments = []
        for s, e in comment_ranges:
            if e <= comment_start and s >= prev_block_end:
                comments.append(text[s:e])
        merged_comments = '\n'.join(comments)
        block_comments.append(merged_comments.strip())
    
    return block_comments

def get_functions_blank_in_contract(text, contract_block):
    start, end = contract_block
    contract_code = text[start:end]
    function_matches = function_pattern.finditer(contract_code)
    code_blank = contract_code
    for match in reversed(list(function_matches)):
        body_start = match.start(5)
        body_end = match.end(5)
        code_blank = code_blank[:body_start] + "{}" + code_blank[body_end:]
    
    return code_blank

def find_dependencies(slither, contract: Contract) -> Set[str]:
    dependencies = set()

    for base in contract.inheritance:
        if isinstance(base, Contract):
            dependencies.add(base.name)
        else:
            dependencies.add(base)

    for function in contract.functions:
        for internal_call in function.internal_calls:
            if isinstance(internal_call, Contract):
                dependencies.add(internal_call.name)
            elif isinstance(internal_call, Function):
                if isinstance(internal_call.contract, Contract):
                    dependencies.add(internal_call.contract.name)

        for high_level_call in function.high_level_calls:
            if isinstance(high_level_call[0], Contract):
                dependencies.add(high_level_call[0].name)

    return dependencies

def combine_contracts(source_code, target_contract: Contract, dependencies: Set[str], output_file: str):
    combined_source = ""
    blocks = extract_blocks(source_code)
    block_comments = extract_comments_above_blocks(source_code, blocks)

    for i, (start, end) in enumerate(blocks):
        contract_code = source_code[start:end]
        contract_name = re.search(r'\b(contract|interface|library|abstract contract)\s+(\w+)', contract_code).group(2)
        if contract_name != target_contract.name and contract_name in dependencies:
            combined_source += block_comments[i] + "\n\n" if block_comments[i] else ""
            combined_source += contract_code + "\n\n"

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(combined_source)

    print(f"{output_file}")

def extract_target_contract_info(source_code, core_name, output_file):
    blocks = extract_blocks(source_code)
    target_block = None
    for start, end in blocks:
        contract_code = source_code[start:end]
        match = re.search(r'\b(contract|interface|library|abstract)\s+(\w+)', contract_code)
        if match and match.group(2) == core_name:
            target_block = (start, end)
            break

    if not target_block:
        print(f"{core_name}")
        return

    code = source_code[target_block[0]:target_block[1]]
    code_blank = get_functions_blank_in_contract(source_code, target_block)

    result = {
        "contract_name": core_name,
        "code": code,
        "code_blank": code_blank
    }
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=4)
    print(f"{output_file}")

def check_low_value(code):
    contract_type = re.search(r'\b(contract|interface|library|abstract contract)\s+(\w+)', code).group(1)
    contract_name = re.search(r'\b(contract|interface|library|abstract contract)\s+(\w+)', code).group(2)

    if contract_type != "contract": return False
    third_party = ['SafeMath', 'Ownable', 'IERC20', 'ERC20', 'Context']
    for name in third_party: 
        if contract_name in third_party: return False
    
    if re.search(r'function\s+\w+$.*?$;', code):
        return False
    if not re.search(r'\b(address|uint|mapping|struct)\b', code):
        return False
    
    return True

def select_random_contract_with_functions(contract_codes):
    contract_name_pattern = re.compile(r'\b(contract|interface|library|abstract contract)\s+(\w+)')
    valid_contracts = [] 
    
    for code in contract_codes:
        name_match = contract_name_pattern.search(code)
        if not name_match: 
            continue 
        
        contract_name = name_match.group(2)
        functions = function_pattern.findall(code)
        function_count = len(functions)
        
        if function_count >= 2:
            signatures = []
            for func in functions:
                name, params, modifiers, returns, _ = func
                signature = f"function {name}({params}) {modifiers.strip()}"
                if returns:
                    signature += f" returns ({returns})"
                signatures.append(signature)
            
            valid_contracts.append({
                "contract_name": contract_name,
                "function_count": function_count,
                "contract_code": code,
                "function_signatures": signatures
            })
    
    if not valid_contracts:
        return None, 0, "", []
    selected_contract = random.choice(valid_contracts)
    
    return (
        selected_contract["contract_name"],
        selected_contract["function_count"],
        selected_contract["contract_code"],
        selected_contract["function_signatures"]
    )

def choose_core_name(source_code):
    blocks = extract_blocks(source_code)
    select_blocks = []
    for i, (start, end) in enumerate(blocks):
        if check_low_value(source_code[start:end]):
            select_blocks.append(source_code[start:end])
    return select_random_contract_with_functions(select_blocks)

def normalize_code(code):
    code = re.sub(r'/\*.*?\*/', '', code, flags=re.DOTALL)
    code = re.sub(r'//.*', '', code)
    code = re.sub(r'\s+', ' ', code).strip()
    return code

def extract_core_contract_dependency(file_path, core_name, output_path, info):
    
    with open(file_path, "r") as f:
        source_code = f.read()
    filename = os.path.splitext(os.path.basename(file_path))[0]
    address = filename[filename.find("_")+1:]

    combined_output_file = os.path.join(output_path, f"{filename}_context.sol")
    json_output_file = os.path.join(output_path, f"{filename}.json")
    
    version = ""
    for contract in info:
        if address in contract["address"]:
            if contract["compiler"][0] == "v":
                version = contract["compiler"][1:]
            else: version = contract["compiler"]
    try:
        subprocess.run(["solc-select", "use", version], check=True)
        slither = Slither(file_path)
    except Exception as e:
        print(file_path, "Wrong!")
        return

    target_contract = None
    for contract in slither.contracts:
        if contract.name == core_name:
            target_contract = contract
            break
    if target_contract == None:
        print(f"{core_name}")
        return

    dependencies = find_dependencies(slither, target_contract)
    with open(os.path.join(output_path, os.path.basename(file_path)), "w") as f:
        f.write(source_code)
    combine_contracts(source_code, target_contract, dependencies, combined_output_file)
    extract_target_contract_info(source_code, core_name, json_output_file)
    

if __name__ == "__main__":
    contract_folder = '../dataset/benchmark_add'
    output_folder = '../dataset/benchmark_third'
    info_path = '../document/top_8000.json'
    
    unique_contracts = {}
    unique_functions = {}
    selected_contracts = []
    for contract in os.listdir(contract_folder):
        solidity_file = os.path.join(contract_folder, contract)
        print(solidity_file)
        with open(solidity_file, "r") as f:
            source_code = f.read()
        if 'import' in source_code: continue
        core_name, core_functions, core_contract_code, core_signature = choose_core_name(source_code)
        
        normalize_contract = normalize_code(core_contract_code)
        print(core_signature)
        if not normalize_contract in unique_contracts:
            unique_contracts[normalize_contract] = contract
            if not core_name in unique_functions:
                unique_functions[core_name] = [core_signature]
                selected_contracts.append((contract, core_name, core_functions))
            else:
                if not core_signature in unique_functions[core_name]:
                    unique_functions[core_name].append(core_signature)
                    selected_contracts.append((contract, core_name, core_functions))
    
    with open("../document/selected_contract.json", "w") as f:
        json.dump(selected_contracts, f, indent=4)
    print(len(selected_contracts))
    
    '''
    with open("../document/selected_contract.json", "r") as f:
        selected_contracts = json.load(f)
    with open(info_path, "r") as f:
        info = json.load(f)
    for (contract, core_name, function_num) in selected_contracts:
        if os.path.exists(os.path.join(output_folder, contract)):
            print(contract)
            extract_core_contract_dependency(os.path.join(contract_folder, contract), core_name, output_folder, info)
    '''
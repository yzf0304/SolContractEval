import os
import json
import shutil
import random

input_path = "../dataset/benchmark_second"
document_path = '../document'
output_path = '../dataset/benchmark_third'

if not os.path.exists(output_path): 
    os.mkdir(output_path)

with open(os.path.join(document_path, "top_8000.json"), "r") as f:
    infos = json.load(f)
with open(os.path.join(document_path, "selected_contract.json"), "r") as f:
    selected = json.load(f)

version_4_candidates = []  
version_8_candidates = []  

for contract_combine in selected:
    contract = contract_combine[0]
    function = contract_combine[1]
    function_num = contract_combine[2]
        
    contract_address = contract[:contract.find(".")]
    address = contract_address[contract_address.find("_")+1:]

    print(address)
    version = ""
    for info in infos:
        if address in info["address"]:
            if info["compiler"][0] == "v":
                version = info["compiler"][1:]
            else: 
                version = info["compiler"]
    
    if version.startswith('0.4'):
        version_4_candidates.append((contract_address, version, contract, function_num))
    elif version.startswith('0.8'):
        version_8_candidates.append((contract_address, version, contract, function_num))
    elif version.startswith(('0.5', '0.6', '0.7')):
        shutil.copy(os.path.join(input_path, contract), output_path)

random.seed(42)  
selected_version_4_contracts = []
selected_version_8_contracts = []

if version_4_candidates:
    version_4_candidates_sorted = sorted(version_4_candidates, key=lambda x: x[3])
    total = len(version_4_candidates_sorted)
    select_num = min(70, int(total * 3/4))
    top_3_4_candidates = version_4_candidates_sorted[:int(total * 3/4)]
    
    selected_version_4 = random.sample(top_3_4_candidates, select_num) if select_num > 0 else []
    for contract_info in selected_version_4:
        contract_address, version, contract, function_num = contract_info
        shutil.copy(os.path.join(input_path, contract), output_path)
        selected_version_4_contracts.append(function_num)

selected_version_8 = random.sample(version_8_candidates, min(70, len(version_8_candidates))) if version_8_candidates else []
for contract_info in selected_version_8:
    contract_address, version, contract, function_num = contract_info
    shutil.copy(os.path.join(input_path, contract), output_path)  
    selected_version_8_contracts.append(function_num)

def calculate_average_function_num(selected_contracts):
    if not selected_contracts:
        return 0
    return sum(selected_contracts) / len(selected_contracts)

avg_func_num_04 = calculate_average_function_num(selected_version_4_contracts)
avg_func_num_08 = calculate_average_function_num(selected_version_8_contracts)

print(f"Selected {len(selected_version_4_contracts)} contracts from version 0.4")
print(f"Average function_num in version 0.4: {avg_func_num_04:.2f}")

print(f"Selected {len(selected_version_8_contracts)} contracts from version 0.8")
print(f"Average function_num in version 0.8: {avg_func_num_08:.2f}")
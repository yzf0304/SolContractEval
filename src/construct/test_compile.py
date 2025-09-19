import os
import numpy as np
import subprocess
import json
import solcx
import shutil
from tqdm import tqdm
from solcx.exceptions import SolcError

def get_installed_versions():
    result = subprocess.run(
        ["solc-select", "versions"],
        stdout=subprocess.PIPE,
        text=True
    )
    return result.stdout.split()

def compile_and_log(version, sol_code, output_file):
    installed = get_installed_versions()
    if version not in installed:
        print(f"{version}")
        subprocess.run(
            ["solc-select", "install", version],
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
    subprocess.run(
        ["solc-select", "use", version],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    parts = version.split(".")
    major, minor, patch = map(int, parts)
    try:
        if minor == 4 and patch < 9:
            compiled = solcx.compile_source(sol_code)
        else:
            compiled = solcx.compile_standard(
                {
                    "language": "Solidity",
                    "sources": {"contract.sol": {"content": sol_code}}
                }
            )
        return True
    except SolcError as e:
        with open(output_file, "w") as f: f.write(str(e))
        return False

def compilation_test(model_name):
    info_path = "../dataset/benchmark_info.json"
    input_path = "../results/generated_contract"
    output_path = "../results/compile_success"
    document_path = "../results/model_performance"
    os.makedirs(os.path.join(output_path, model_name), exist_ok=True)
    with open(info_path, "r") as f:
        info = json.load(f)
    success_sum_list = {}

    contract_folders = [f for f in os.listdir(os.path.join(input_path, model_name))]
    for contract_folder in tqdm(contract_folders, desc = "Compiling Contracts"):
        success_sum = 0
        correct_file = []
        sample_folder_path = os.path.join(input_path, model_name, contract_folder)
        compile_success_path = os.path.join(output_path, model_name, contract_folder)
        os.makedirs(compile_success_path, exist_ok=True)

        for test_file in os.listdir(sample_folder_path):
            if test_file.endswith("sol"):
                contract_id = contract_folder
                only_address = contract_id[contract_id.find("_")+1:]
                version = ""
                for contract_info in info:
                    if only_address in contract_info["address"]:
                        if contract_info["compiler"][0] == "v":
                            version = contract_info["compiler"][1:]
                        else: version = contract_info["compiler"]

                contract_file = os.path.join(sample_folder_path, test_file)
                compile_out_file = os.path.join(sample_folder_path, test_file[:test_file.find(".")] + "_compile.txt")
                if os.path.exists(compile_out_file): os.remove(compile_out_file)
                with open(contract_file, "r") as f:
                    source_code = f.read()

                flag = compile_and_log(version, source_code, compile_out_file)
                if flag: 
                    success_sum += 1
                    shutil.copy(contract_file, compile_success_path)
                    correct_file.append(test_file)
        success_sum_list[contract_id] = {"correct_sum": success_sum, "correct_list": correct_file }
    
    with open(os.path.join(document_path, f"{model_name}_compile.json"), "w", encoding='utf-8') as f:
        json.dump(success_sum_list, f, indent=4)

        

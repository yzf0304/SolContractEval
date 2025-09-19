import os
import json
import re
from solcx import compile_source, install_solc
import subprocess
import requests

def generate_contract_bytecode(source_file, contract):
    version = contract["Compiler Version"]
    if version[0] == "v": version = version[1:]
    if version.find("+")!=-1: version = version[:version.find("+")]
    if version.find("-")!=-1: version = version[:version.find("-")]
    subprocess.run(
        ["solc-select", "use", version],
        check=True,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    with open(source_file, "r", encoding="UTF-8") as f:
        source_code = f.read()
    
    optimized = contract["Optimization Enabled"]
    if "Yes" in optimized:
        optimizer_enabled = True
        numbers = re.findall(r'\d+', optimized)
        optimizer_runs = int(numbers[0]) if numbers else 200
    else:
        optimizer_enabled = False
        optimizer_runs = 0
    compiled_sol = compile_source(source_code, output_values=["bin"], optimize = optimizer_enabled, optimize_runs = optimizer_runs)
    contract_name = contract["name"]
    bytecode = compiled_sol["<stdin>:"+contract_name]["bin"]
    constructor_argument = contract["constructor_argument"]

    return "0x" + bytecode + constructor_argument

def switch_bytecode(new_bytecode, test_file, output_path):
    with open(test_file, 'r', encoding='utf-8') as file:
        content = file.read()
    
    pattern = r'"input"\s*:\s*"([^"]+)"'
    match = re.search(pattern, content)
    updated_content = content[:match.start(1)] + new_bytecode + content[match.end(1):]
    with open(os.path.join(output_path, os.path.basename(test_file)), "w", encoding="utf-8") as file:
        file.write(updated_content)
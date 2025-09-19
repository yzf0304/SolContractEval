import subprocess
import json
import re
from solcx import compile_source, set_solc_version, install_solc, get_installed_solc_versions
from slither.slither import Slither
import time
import os

def set_solc_version_globally(solc_version):
    
    installed_versions = subprocess.run(['solc-select', 'versions'], capture_output=True, text=True)
    if solc_version not in installed_versions.stdout:
        
        subprocess.run(['solc-select', 'install', solc_version], check=True)
    
    subprocess.run(['solc-select', 'use', solc_version], check=True)

def get_solc_version(contract_file):
    with open(contract_file, 'r') as file:
        source = file.read()
    
    version_lines = [line for line in source.split('\n') if 'pragma solidity' in line]
    versions = {'0.4.11'}
    
    for line in version_lines:
        match = re.search(r'pragma solidity\s*([^;]+);', line)
        if match:
            version_spec = match.group(1)
            if '^' in version_spec:
                
                versions.add(version_spec.split('^')[-1].strip())
            elif '>=' in version_spec:
                
                versions.add(version_spec.split('>=')[-1].strip())
            
    
    
    
    return max(versions, key=lambda v: [int(x) for x in v.split('.')])


def compile_contract_for_abi_and_bytecode(contract_file, solc_version):
    installed_versions = get_installed_solc_versions()
    if solc_version not in installed_versions:
        install_solc(solc_version)
    set_solc_version(solc_version)
    with open(contract_file, 'r') as file:
        source = file.read()
    compiled_sol = compile_source(source)

    contract_data = {}
    for contract_id, contract_interface in compiled_sol.items():
        
        contract_name = str(contract_id).split(':')[1]
        contract_data[contract_name] = {
            'abi': contract_interface.get('abi'),
            'bytecode': contract_interface.get('bin')
        }
    return contract_data

def analyze_contract_with_slither(contract_file, solc_version):
    
    installed_versions = get_installed_solc_versions()
    if solc_version not in installed_versions:
        install_solc(solc_version)
    set_solc_version_globally(solc_version)
    slither = Slither(contract_file)
    return slither

def compile_and_analyze_contract(contract_address, contract_file, etherscan_api, solc_version=None):
    if solc_version !=None:
        solc_version = solc_version.split('+')[0][1:]
        if solc_version.startswith('0.4.') and int(solc_version.split('.')[-1]) <= 17:
            solc_version = '0.4.17'
    slither_instances = analyze_contract_with_slither(contract_file, solc_version)
    return None, slither_instances

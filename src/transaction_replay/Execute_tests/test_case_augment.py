import copy
import itertools
import os
import json
import requests
from web3 import Web3
from collections import Counter
import subprocess
import tempfile
from .switch_test_cases import generate_contract_bytecode


def save_new_test_cases(test_case_folder, bytecode):
    with open(os.path.join(test_case_folder, '0.json'), 'r') as f:
        test_cases = json.load(f)
    test_cases[0]["input"] = bytecode
    with open(os.path.join(test_case_folder, '0_new.json'), 'w') as f:
        json.dump(test_cases, f, indent=4)
    return

def execute_transactions_with_storage_layout(transactions, layout, should_record_trace = []):
    with tempfile.TemporaryDirectory(dir="./transaction_replay/Execute_tests/Hardhat") as temp_dir:
        test_case_path = os.path.join(temp_dir, 'test_cases.json')
        with open(test_case_path, 'w') as f:
            json.dump(transactions, f)
        should_record_trace = list(should_record_trace)
        should_record_trace = ['"' + x + '"' for x in should_record_trace]
        js_should_record_trace = F"{','.join(should_record_trace)}"
        js_slot_layout = json.dumps(layout, indent=2)

        script_path = os.path.join(temp_dir, 'execute_transactions.js')
        with open("./transaction_replay/Documents/scripts/execute_transaction.js", "r") as file:
            script_content = file.read()
        
        with open(script_path, 'w') as script_file:
            script_file.write(script_content.format(js_slot_layout = js_slot_layout))

        
        config_path = os.path.join(temp_dir, 'hardhat.config.js')
        with open(config_path, 'w') as config_file:
            config_file.write(f"""
            require("@nomiclabs/hardhat-waffle");
            require("@nomiclabs/hardhat-ethers");

            module.exports = {{
                networks: {{
                    hardhat: {{
                        allowUnlimitedContractSize: true,
                        blockGasLimit: 1000000000  
                    }}
                }}
            }};
            """)

        
        command = 'npx hardhat run execute_transactions.js'
        subprocess.run(command, shell=True, cwd=temp_dir)
        result = {}
        for result_file in os.listdir(temp_dir):
            if 'result' not in result_file:
                continue
            txhash = result_file.split('_result')[0]
            try:
                with open(os.path.join(temp_dir, result_file),'r') as f:
                    result[txhash] = json.load(f)
            except Exception as e:
                continue
        return result

def execute_test_cases_in_folder_and_record_trace(test_case_folder, layout):
    for file in os.listdir(test_case_folder):
        test_case_id = file.split('.')[0]
        if file.endswith('.json') and test_case_id.find("new")!=-1 and test_case_id.find("result")==-1 :
            with open(os.path.join(test_case_folder, file), 'r') as f:
                transactions = json.load(f)
                transaction_hashes = [tx['hash'] for tx in transactions]
                # result = execute_transactions(transactions, transaction_hashes)
                result = execute_transactions_with_storage_layout(transactions, layout, transaction_hashes)
                with open(os.path.join(test_case_folder, test_case_id+"_result.json"), 'w+') as fo:
                    json.dump(result, fo)

def levenshtein_distance(tup1, tup2):
    
    dp = [[0] * (len(tup2) + 1) for _ in range(len(tup1) + 1)]
    for i in range(len(tup1) + 1):
        dp[i][0] = i
    for j in range(len(tup2) + 1):
        dp[0][j] = j
    for i in range(1, len(tup1) + 1):
        for j in range(1, len(tup2) + 1):
            if tup1[i-1] == tup2[j-1]:
                cost = 0
            else:
                cost = 1
            dp[i][j] = min(dp[i-1][j] + 1,      
                           dp[i][j-1] + 1,      
                           dp[i-1][j-1] + cost) 

    return dp[-1][-1]

def tuples_similar(tup1, tup2, threshold_ratio):
    if (len(tup1)<=1 and len(tup2) > 1 or len(tup1) > 1 and len(tup2)<=1):
        return False
    min_len = min(len(tup1), len(tup2), 10000)
    max_distance = int(min_len * threshold_ratio)
    distance = levenshtein_distance(tup1[:min_len-1], tup2[:min_len-1])

    return distance <= max_distance

def same_trace(trace_a, trace_b, is_internal = False):
    if trace_a is None or trace_b is None:
        return False
    if 'failed' not in trace_a or 'failed' not in trace_b:
        return False

    if is_internal:
        execution_path_a = tuple((step['op']) for step in trace_a['structLogs'] if step['op'] not in ['KECCAK256', 'SHA3', 'POP', 'JUMPDEST', 'JUMP'])
        execution_path_b = tuple((step['op']) for step in trace_b['structLogs'] if step['op'] not in ['KECCAK256', 'SHA3', 'POP', 'JUMPDEST', 'JUMP'])
        if trace_a['failed'] == True and trace_b['failed'] == False:
            if not ('INVALID' in execution_path_b or "REVERT" in execution_path_b):
                return False

        result = tuples_similar(execution_path_a, execution_path_b, threshold_ratio = 0.1)
        return result
    else:
        if trace_a['failed'] != trace_b['failed']:
            return False
        execution_path_a = tuple((step['pc'], step['op']) for step in trace_a['structLogs'] if step['op']!='KECCAK256' and step['op']!='SHA3')
        execution_path_b = tuple((step['pc'], step['op']) for step in trace_b['structLogs'] if step['op']!='KECCAK256' and step['op']!='SHA3')
        result = tuples_similar(execution_path_a, execution_path_b, 0.3)
        return result

def check_trace(test_case_folder):
    # print("Comparing the execution results of trace before and after the modification in the folder", test_case_folder)
    file1 = "0_result.json"
    file2 = "0_new_result.json"
    with open(os.path.join(test_case_folder, file1), 'r') as f:
        result1 = json.load(f)
    with open(os.path.join(test_case_folder, file2), 'r') as f:
        result2 = json.load(f)

    sum_same = 0
    for tx in result1.keys():
        trace1 = result1[tx]["trace"]
        trace2 = result2[tx]["trace"]
        if same_trace(trace1, trace2):
            sum_same += 1
    return sum_same

def check_log(test_case_folder):
    # print("Comparing the execution results of logs in the contract", os.path.basename(test_case_folder))
    file1 = "0_result.json"
    file2 = "0_new_result.json"
    with open(os.path.join(test_case_folder, file1), 'r') as f:
        result1 = json.load(f)
    with open(os.path.join(test_case_folder, file2), 'r') as f:
        result2 = json.load(f)      
        
    sum_same = 0     
    for tx in result1.keys():
        has_receipt1 = "receipt" not in result1[tx]
        has_receipt2 = "receipt" not in result2[tx]
        if has_receipt1 == has_receipt2:
            if has_receipt1 == True:
                if result1[tx]["receipt"]["logs"] == result2[tx]["receipt"]["logs"]:
                    sum_same += 1
                else: continue
            else: sum_same += 1
        else: continue

    return sum_same

def check_returnvalue(test_case_folder):
    # print("Comparing the execution results of returnvalue in the contract", os.path.basename(test_case_folder))
    file1 = "0_result.json"
    file2 = "0_new_result.json"
    with open(os.path.join(test_case_folder, file1), 'r') as f:
        result1 = json.load(f)
    with open(os.path.join(test_case_folder, file2), 'r') as f:
        result2 = json.load(f)      
        
    sum_same = 0     
    for tx in result1.keys():
        if result1[tx]["logs"] == result2[tx]["logs"]:
            if result1[tx]["trace"]["failed"] == result1[tx]["trace"]["failed"]:
                if result1[tx]["trace"]["returnValue"] == result2[tx]["trace"]["returnValue"]:
                    sum_same += 1

    return sum_same

def check_state(test_case_folder):
    # print("Comparing the execution results of state in the contract", os.path.basename(test_case_folder))
    file1 = "0_result.json"
    file2 = "0_new_result.json"
    with open(os.path.join(test_case_folder, file1), 'r') as f:
        result1 = json.load(f)
    with open(os.path.join(test_case_folder, file2), 'r') as f:
        result2 = json.load(f)
    
    sum_same = 0     
    for tx in result1.keys():
        if "state" not in result1[tx] and "state" not in result2[tx]: 
            sum_same += 1
            continue
        
        state1 = result1[tx]["state"]
        state2 = result2[tx]["state"]
        if state1 == state2: sum_same += 1
        
    return sum_same

def test_replayer_and_recorder(source_contract_file, args):
    '''source_contract_file: contract_name + contract_address +.sol'''
    contract_id = source_contract_file['id']
    print("-"*10, "Executing test cases for", contract_id, "-"*10)
    test_case_folder = os.path.join(args.contract_folder, "Transaction_Trace", f'test_case_{args.max_transactions}', contract_id)
    layout_folder = os.path.join(args.contract_folder, "Layout")
    with open(os.path.join(layout_folder, f"{contract_id}.json"), "r") as f:
        layout = json.load(f)

    correct_list = []
    for contract in os.listdir(os.path.join("../results/compile_success", args.model_name, contract_id)):
        # print(contract)
        if contract.endswith("sol"):

            bytecode = generate_contract_bytecode(os.path.join("../results/compile_success", args.model_name, contract_id, contract), source_contract_file)
            save_new_test_cases(test_case_folder, bytecode)
            execute_test_cases_in_folder_and_record_trace(test_case_folder, layout)

            log = check_log(test_case_folder)
            state = check_state(test_case_folder)
            returnvalue = check_returnvalue(test_case_folder)
            
            correct_list.append((contract, log, state, returnvalue))
        
    return correct_list

    
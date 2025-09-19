import os
import json
import argparse
import numpy as np
from construct.concatenate import concatenate
from construct.test_compile import compilation_test
from calc_metric import calc_compile_k, calc_pass_k
from transaction_replay.Execute_tests.test_case_augment import test_replayer_and_recorder
from tqdm import tqdm

def main():
    parser = argparse.ArgumentParser(description="SolContractEval Test")
    parser.add_argument('--model_name', type=str, required=True, help='Model name for testing')
    parser.add_argument('--contract_folder', type=str, required=True, help='Path to the folder containing contract information and for executing')
    parser.add_argument('--model_output_folder', type=str, required=True, help='Path to the folder containing model outputs')
    parser.add_argument('--max_transactions', type=int, default=1000, help='Maximum number of transactions to process')

    args = parser.parse_args()
    print("#"*20, "Concatenate model responses with original context", "#"*20)
    total, success = concatenate(args.model_output_folder, args.model_name)
    print(f"total response: {total}, success: {success}")

    print("#"*20, "Test the compilation correctness of generated contracts", "#"*20)
    compilation_test(args.model_name)
    calc_compile_k(args.model_name)

    print("#"*20, "Test the functional correctness of generated contracts", "#"*20)
    execute_test_cases(args)
    calc_pass_k(args.model_name)

def execute_test_cases(args):
    result_file = os.path.join("../results/model_performance", args.model_name + "_test.json")

    contract_files = []
    for contract in os.listdir(os.path.join(args.model_output_folder, args.model_name)):
        with open(os.path.join(args.contract_folder,"Contract_Info/", contract + ".json"), "r") as fr:
            contract = json.loads(fr.read())
            contract['file'] = os.path.join(args.contract_folder, contract['file'][2:])
        contract_files.append(contract)
    
    correct_dict = {}
    for contract in contract_files:
        
        try:
            correct_info_list = test_replayer_and_recorder(contract, args)
        except Exception as e:
            correct_info_list = []

        correct_sum = 0
        correct_list = []
        for (answer, correct_log, correct_state, correct_returnvalue) in correct_info_list:
            if min(correct_log, correct_state, correct_returnvalue) >= (args.max_transactions - 1): 
                correct_sum += 1
                correct_list.append(answer)

        correct_dict[contract["id"]] = {
            "correct_sum": correct_sum,
            "correct_list": correct_list
        }
        print(correct_dict[contract["id"]])

    with open(result_file, "w") as f:
        json.dump(correct_dict, f, indent=4)
    return correct_dict
    
if __name__ == "__main__":
    main()
import os
import shutil
import subprocess
import json
import argparse
from switch_test_cases import generate_contract_bytecode, switch_bytecode
from test_case_augment import execute_test_cases_in_folder_and_record_trace, test_replayer_and_recorder
import numpy as np

def main():
    parser = argparse.ArgumentParser(description="SolContractEval")
    parser = argparse.ArgumentParser(description="SolMigrator: A tool for migrating and augmenting Solidity contract test cases.")
    parser.add_argument('--contract_folder', type=str, required=True,
                        help='Path to the folder containing original Solidity contracts.')
    parser.add_argument('--test_contract_folder', type=str, required=True,
                        help='Path to the folder containing test contracts corresponding to the originals.')
    parser.add_argument('--contract', type=str, default='',
                        help='Name of a specific contract to process. If not set, all contracts in the folder will be used.')
    parser.add_argument('--model_name', type=str, required=True,
                        help='Name or path of the model used for generating migrated contracts.')
    parser.add_argument('--sample_num', type=str, required=True,
                        help='Number of generated samples to use per contract (e.g., 1, 3, or "all").')
    parser.add_argument('--augmentation_folder', type=str, required=True,
                        help='Path to the output folder where augmented test cases will be saved.')
    parser.add_argument('--max_transactions', type=int, default=100,
                        help='Maximum number of transactions to include per test case.')


    args = parser.parse_args()
    correct_list = execute_test_cases(args)
    calc_pass_k(correct_list, 1)
    calc_pass_k(correct_list, 3)
    calc_pass_k(correct_list, 5)

def estimator(n, c, k):
    if n - c < k:
        return 1.0
    return (1.0 - np.prod(1.0 - k / np.arange(n - c + 1, n + 1)))

def calc_pass_k(correct_list, k, n = 5):
    average_pass_k = sum(estimator(n, item["correct_sum"], k) for item in correct_list) / len(correct_list)
    print(f"Average Pass@{k}: {average_pass_k:.4f}")

def execute_test_cases(args):
    if not os.path.exists(os.path.join(args.contract_folder, "results")):
        os.mkdir(os.path.join(args.contract_folder, "results"))
    if not os.path.exists(os.path.join(args.contract_folder, "results", f"transaction_{args.max_transactions}")):
        os.mkdir(os.path.join(args.contract_folder, "results", f"transaction_{args.max_transactions}"))
    if not os.path.exists(os.path.join(args.contract_folder, "new_bytecode")):
        os.mkdir(os.path.join(args.contract_folder, "new_bytecode"))
    
    result_file = os.path.join(args.contract_folder, "results", f"transaction_{args.max_transactions}", args.model_name + ".json")
    print(result_file)
    # if os.path.exists(result_file):
    #     with open(result_file, "r") as f:
    #         return (json.load(f))

    contract_files = []
    for contract in os.listdir(os.path.join(args.test_contract_folder, args.model_name)):
        with open(os.path.join(args.contract_folder,"Contract_Info/", contract + ".json"), "r") as fr:
            contract = json.loads(fr.read())
            contract['file'] = os.path.join(args.contract_folder, contract['file'][2:])
        contract_files.append(contract)
    if args.contract != '':
        contract_files = [x for x in contract_files if x['id'] == args.contract]
    
    print(len(contract_files))
    correct_list = []
    sum = 1
    for contract in contract_files:
        print(f"testing {sum}")
        sum += 1
        try:
            correct_info_list = test_replayer_and_recorder(contract, args)
        except Exception as e:
            print("Failed augmentation due to", e)
            correct_info_list = []
        correct_sum = 0
        for (_, correct_log, correct_state, correct_returnvalue) in correct_info_list:
            if min(correct_log, correct_state, correct_returnvalue) >= (args.max_transactions - 1): correct_sum += 1

        correct_list.append({
            "address": contract["id"],
            "correct_info_list": correct_info_list,
            "correct_sum": correct_sum
        })

    with open(result_file, "w") as f:
        json.dump(correct_list, f, indent=4)
    return correct_list
    
if __name__ == "__main__":
    main()
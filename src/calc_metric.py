import os
import argparse
import numpy as np
import json

def main():
    parser = argparse.ArgumentParser(description="SolContractEval Test")
    parser.add_argument('--model_name', type=str, required=True, help='Path to the folder containing generated contract')
    args = parser.parse_args()

    calc_compile_k(args.model_name)
    calc_pass_k(args.model_name)

def estimator(n, c, k):
    if n - c < k:
        return 1.0
    return (1.0 - np.prod(1.0 - k / np.arange(n - c + 1, n + 1)))

def calc_compile_k(model_name):
    result_path = "../results/model_performance"
    os.makedirs(result_path, exist_ok=True)
    with open(os.path.join(result_path, model_name + "_compile.json"), "r") as f:
        contract_data = json.load(f)
    contracts = contract_data.values()
    total_contracts = len(contracts)

    correct_sum = 0
    for contract in contracts:
        if "output0.sol" in contract["correct_list"]:
            correct_sum += 1
    print(f"Average Compile@1: {correct_sum/total_contracts:.4f}")  

    for k in [3, 5]:
        total_score = 0
        for contract in contracts:
            correct = contract["correct_sum"]
            score = estimator(5, correct, k)
            total_score += score
        average_compile_k = total_score / total_contracts
        print(f"Average Compile@{k}: {average_compile_k:.4f}")

def calc_pass_k(model_name):
    result_path = "../results/model_performance"
    with open(os.path.join(result_path, model_name + "_test.json"), "r") as f:
        contract_data = json.load(f)
    contracts = contract_data.values()
    total_contracts = len(contracts)

    correct_sum = 0
    for contract in contracts:
        if "output0.sol" in contract["correct_list"]:
            correct_sum += 1
    print(f"Average Pass@1: {correct_sum/total_contracts:.4f}")  

    for k in [3, 5]:
        total_score = 0
        for contract in contracts:
            correct = contract["correct_sum"]
            score = estimator(5, correct, k)
            total_score += score
        average_pass_k = total_score / total_contracts
        print(f"Average Pass@{k}: {average_pass_k:.4f}")
    
if __name__ == "__main__":
    main()
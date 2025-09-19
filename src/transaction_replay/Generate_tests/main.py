from test_case_augment import test_replayer_and_recorder
import os
import shutil
import argparse
import os
import json
from slither import Slither
import subprocess
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="eth_utils.network")


def main():
    parser = argparse.ArgumentParser(description="SolContractEval")
    parser.add_argument('--contract_folder', type=str, required=True,
                    help='Path to the folder containing original Solidity contracts.')
    parser.add_argument('--contract', type=str, default='',
                        help='Name of a specific contract to process. If not set, all contracts in the folder will be processed.')
    parser.add_argument('--augmentation_folder', type=str, required=True,
                        help='Path to the folder where augmented test cases will be saved.')
    parser.add_argument('--max_transactions', type=int, default=100,
                        help='Maximum number of historical transactions to include per contract.')
    parser.add_argument('--etherscan_api', type=str, required=True,
                        help='Etherscan API key used to retrieve historical transactions.')
    parser.add_argument('--test_contract_folder', type=str, default=1000,
                        help='Path to the folder containing the test contracts. (Note: the default value seems incorrect; expected a string path, not an int).')


    args = parser.parse_args()
    generate_test_cases(args)

def generate_test_cases(args):
    if not os.path.exists(args.augmentation_folder):
        os.makedirs(args.augmentation_folder, exist_ok=True)
    if not os.path.exists(os.path.join(args.augmentation_folder, f'augmented_test_case_{args.max_transactions}')):
        print("Making new dir to store augmented test cases:", os.path.join(args.augmentation_folder, f'augmented_test_case_{args.max_transactions}'))
        os.makedirs(os.path.join(args.augmentation_folder, f'augmented_test_case_{args.max_transactions}'))
    if not os.path.exists(os.path.join(args.augmentation_folder, 'layout')):
        print("Making new dir to store storage layout:", os.path.join(args.augmentation_folder, 'layout'))
        os.makedirs(os.path.join(args.augmentation_folder, 'layout'))
    
    contract_files = []
    for f in os.listdir(os.path.join(args.contract_folder,"Contract_Info/")):
        with open(os.path.join(args.contract_folder,"Contract_Info/", f), "r") as fr:
            contract = json.loads(fr.read())
            if contract['file'][0:2] == "./": 
                contract['file'] = contract['file'][2:]
            contract['file'] = os.path.join(args.contract_folder, contract['file'])

            test_file = os.path.join(args.test_contract_folder, contract["id"]+".sol")
            if os.path.exists(test_file):
                contract_files.append(contract)
    if args.contract != '':
        contract_files = [x for x in contract_files if x['id'] == args.contract]
        
    for contract in contract_files:
        try:
            test_replayer_and_recorder(contract, args)
        except Exception as e:
            print("❌ Failed augmentation due to", e)
            continue

if __name__ == "__main__":
    main()


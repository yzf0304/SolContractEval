# SolContractEval

## Overview

This directory contains the test source code for **SolContractEval**, a framework designed to evaluate smart contract generation models.

## Environment

- **Python version**: 3.10.0  
- **Operating system**: Linux

## Installation

Follow these steps to set up the environment:

```bash
cd ./src
pip3 install -r requirements.txt
cd ./src/transaction_replay/Execute_tests/Hardhat
npm install --save-dev hardhat @nomicfoundation/hardhat-toolbox 
```

## Usage

### Testing the Model performance

You can view the usage of the test command with the following command:

```bash
python test_results.py --help
python test_results.py [-h] --model_name MODEL_NAME --contract_folder CONTRACT_FOLDER --model_output_folder MODEL_OUTPUT_FOLDER [--max_transactions MAX_TRANSACTIONS]

options:
  -h, --help            Show this help message and exit
  --model_name MODEL_NAME
                        Model name for testing
  --contract_folder CONTRACT_FOLDER
                        Path to the folder containing contract information and for executing
  --model_output_folder MODEL_OUTPUT_FOLDER
                        Path to the folder containing model outputs
  --max_transactions MAX_TRANSACTIONS
                        Maximum number of transactions to process                                            
```

**Example**

For example, users can run the following command to reproduce the results:

```bash
cd ./src
python test_results.py --model_name gpt-4o --contract_folder ../results/transaction_replay --model_output_folder ../results/model_output --max_transactions 1000
```


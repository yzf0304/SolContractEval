# results

This directory contains the dataset of SolContractEval. Specifically, it contains the following directories:

- `./model_output/`: Contains the complete output results of all models under benchmark tests
- `./transaction_replay/`: Records all functional test cases and intermediate process files during testing
- `./model_performance/`: Summarizes the final performance evaluation metrics of each model
- `./generated_contract/`: Integrates source code extracted from `./model_output/` and merges it with contextual components to form complete contract code
- `./compile_success/`: Includes successfully compiled `./generated_contract/` for subsequent functional testing
import os
import subprocess
import sys

def execute_migrated_test_cases_with_assertions(migrated_test_folder, hardhat_folder):
    for root, _, files in os.walk(migrated_test_folder):
        for file in files:
            if file.endswith(".test.js"):
                file_path = os.path.join(root, file)
                relative_file_path = os.path.relpath(file_path, hardhat_folder)
                original_cwd = os.getcwd()
                os.chdir(hardhat_folder)
                command = f"npx hardhat test {relative_file_path}"
                result = subprocess.run(command, shell=True, capture_output=True, text=True)
                print(result)
                os.chdir(original_cwd)
        
import os
import shutil
input_path = "/home/zhifanye/codegen/SolContractEval/dataset/prompt"
output_path = "/home/zhifanye/codegen/SolContractEval/dataset/source_code"

for contract in os.listdir(input_path):
    if contract.endswith("sol"):
        shutil.move(os.path.join(input_path, contract), output_path)

input_path = "/home/zhifanye/codegen/SolContractEval/results/model_output"
for model in os.listdir(input_path):
    for contract in os.listdir(os.path.join(input_path, model)):
        for txt in os.listdir(os.path.join(input_path, model, contract)):
            if not txt.endswith("txt"): os.remove(os.path.join(input_path, model, contract, txt))
            if "compile" in txt: os.remove(os.path.join(input_path, model, contract, txt))

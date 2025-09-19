import json
import os
import shutil

input_path = "../dataset/benchmark_third"
output_path = "../dataset/benchmark_fourth"
comment_path = "../dataset/benchmark_comments"
contracts_path = "../dataset/benchmark_initial"
info_path = "../document/top_8000.json"
with open(info_path, "r") as f:
    info = json.load(f)
if not os.path.exists(output_path): os.mkdir(output_path)

sum = 0 
for contract in os.listdir(comment_path):
    if contract.endswith("txt"):
        address = os.path.splitext(contract)[0]
        only_address = address[address.find("_")+1:]
        txt_path = os.path.join(comment_path, contract)
        sol_path = os.path.join(input_path, f"{address}_context.sol")
        json_path = os.path.join(input_path, f"{address}.json")

        with open(json_path, "r") as f: data = json.load(f)
        with open(sol_path, "r") as f: context = f.read()
        with open(txt_path, "r") as f: content_new_comments = f.read()
        content = content_new_comments[12:]
        content = content[:content.find("```")]

        test = {}
        contract_name = data["contract_name"]
        test["contract_name"] = data["contract_name"]
        test["ground_truth"] = data["code"]
        test["function_sum"] = data["code_blank"].count("{}")
        version = ""
        for contract_info in info:
            if only_address in contract_info["address"]:
                if contract_info["compiler"][0] == "v":
                    version = contract_info["compiler"][1:]
                else: version = contract_info["compiler"]
        test["compiler_version"] = version

        context_description = f"// Below are some contexts potentially relevant to contract code generation.\n\n"
        task_description = f"// You task is to complete the smart contract {contract_name} strictly according to the provided context and description. Note that the contract is deployed using compiler version {version}, and do not introduce any additional contracts, dependencies, or unrelated code. Deliver only the complete and functional target contract without any extraneous implementations or examples.\n\n"
        
        prompt = context_description + context + "\n\n" + task_description + content
        
        test["prompt"] = prompt

        output_file = os.path.join(output_path, address+".json")
        with open(output_file, "w") as f:
            json.dump(test, f, indent=4)
        
        source_code_path = os.path.join(contracts_path, address + ".sol")
        shutil.copy(source_code_path, output_path)
        sum += 1
print(sum)
        
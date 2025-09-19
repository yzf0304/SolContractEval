import json
import os
import shutil

contract_folder = "../dataset/benchmark_second"
output_path = "../dataset/benchmark_third"
if not os.path.exists(output_path): os.mkdir(output_path)

comments = {}
for contract in os.listdir(output_path):
    if contract.endswith("json"):
        file_path = os.path.join(output_path, contract)
        sol_name = os.path.splitext(contract)[0]
        sol_path = os.path.join(output_path, f"{sol_name}_context.sol")
        with open(file_path, "r") as f:
            data = json.load(f)
        comment = data["comment"]

        # if comment in comments:
        #     os.remove(file_path)
        #     os.remove(sol_path)
        # else:
        #     comments[comment] = 1

        if "@dev" in comment:
            comments[comment] = 1

with open("document/comments.json", "w") as f:
    json.dump(comments, f, indent=4)  

counts = []
for contract in os.listdir(output_path):
    if contract.endswith("sol"):
        file_path = os.path.join(output_path, contract)
        with open(file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            line_count = len(lines)
        counts.append(line_count)
        # print(contract, line_count)
with open("document/line_count.txt", "w") as f:
    sorted_count = sorted(counts)
    for count in sorted_count:
        f.write(str(count) + "\n")
print(sum(counts) / len(counts))
print(max(counts))
print(min(counts))
print(len(counts))
        
        
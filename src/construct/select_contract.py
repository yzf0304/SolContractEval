import json
import os
import shutil
import urllib.request,urllib.error

contract_folder = "/data/zhifanye/contract_code"
output_folder = "/home/zhifanye/codegen/data_process/benchmark_contruct/dataset/benchmark_initial"
if not os.path.exists(output_folder): os.mkdir(output_folder)
with open("../document/top_8000.json", "r") as f:
    contract_info = json.load(f)

total_sum = 0
for info in contract_info:
    address = info["address"]
    name = info['name']
    file_name = f"{name}_{address}.sol"

    begin = address[2:4]
    file_path = os.path.join(contract_folder, begin, file_name)
    output_path = os.path.join(output_folder, file_name)
    
    print(file_path)
    print(output_path)
    if os.path.exists(file_path):
        shutil.copy(file_path, output_path)
        total_sum += 1
    else:
        print(file_path, "wrong")

print(total_sum)

import requests
import json
import urllib.request,urllib.error
from bs4 import BeautifulSoup
import os

proxies = {
    'https': 'https://127.0.0.1:10808',     
    'http': 'http://127.0.0.1:10808',       
}
head = { 
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.93 Safari/537.36"
}
# opener = urllib.request.build_opener(urllib.request.ProxyHandler(proxies))
# urllib.request.install_opener(opener)

def get_contract_info(address, api_key):
    url = f'https://api.etherscan.io/v2/api?chainid=1&module=contract&action=getsourcecode&address={address}&apikey={api_key}'
    print(url)
    request = urllib.request.Request(url, headers=head, method="GET")
    response = urllib.request.urlopen(request, timeout=30)
    data = response.json()
    if data['status'] == '1':
        info = data['result']
    
    url = f'https://api.etherscan.io/v2/api?chainid=1&module=contract&action=getcontractcreation&address={address}&apikey={api_key}'
    print(url)
    request = urllib.request.Request(url, headers=head, method="GET")
    response = urllib.request.urlopen(request, timeout=30)
    data = response.json()
    if data['status'] == '1':
        bytecode = data['result']["creationBytecode"]

    if info and bytecode:
        contract_info = {}
        contract_info["name"] = info["ContractName"]
        contract_info["address"] = address
        contract_info["Compiler Version"] = info["CompilerVersion"]
        if info["OptimizationUsed"] == 1:
            contract_info["Optimization Enabled"] = f"Yes with {info["Runs"]} runs"
        else: contract_info["Optimization Enabled"] = f"No with 0 runs"
        contract_info["creation_bytecode"] = bytecode
        contract_info["abi"] = info["ABI"]
        contract_info["constructor_argument"] = info["ConstructorArguments"]
        contract_info["Contract Source Code"] = info["SourceCode"]
        contract_info["id"] = f"{info["ContractName"]}_{address}"
        contract_info["file"] = f"./Contract_source_Code/{contract_info["id"]}.sol"

        return contract_info

def get_transactions(address, api_key, startblock=0, endblock=99999999, page=1, offset=10000, sort='asc'):
    url = f'https://api.etherscan.io/api?module=account&action=txlist&address={address}&startblock={startblock}&endblock={endblock}&page={page}&offset={offset}&sort={sort}&apikey={api_key}'
    request = urllib.request.Request(url, headers=head, method="GET")
    response = urllib.request.urlopen(request, timeout=30)
    data = response.json()
    if data['status'] == '1':
        return data["result"]


api_key = os.environ.get("ETHERSCAN_API_KEY")
input_path = "../dataset/benchmark_third"
output_path = "../dataset/Contract_Info"
output2_path = "../dataset/Tx_History"
contracts = []

for contract in os.listdir(input_path):
    if contract.endswith("json"):
        address = contract[:contract.find("_")]
        name = contract[contract.find("_")+1:contract.find(".")]
        print(address, name)
        contract_info = get_contract_info("0x"+address, api_key)
        with open(os.path.join(output_path, f"{name}_0x{address}.json"), "r") as f:
            json.dump(contract_info, f)
        
        transactions = get_transactions("0x"+address, api_key)
        with open(os.path.join(output2_path, f"{name}_0x{address}.json"), "r") as f:
            json.dump(transactions, f)
        break

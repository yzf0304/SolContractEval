import copy
import itertools
import os
import json
import requests
from web3 import Web3
from collections import Counter
import subprocess
import tempfile
import time
import shutil

def save_test_cases(test_case_folder, test_cases):
    print(f"Saving test cases in folder {test_case_folder}")
    if not os.path.exists(test_case_folder):
        os.makedirs(test_case_folder)
    with open(os.path.join(test_case_folder, '0.json'), 'w+') as f:
        json.dump(test_cases, f, indent=4)
    return

def execute_transactions(transactions, should_record_trace = []):

    with tempfile.TemporaryDirectory(dir="./Hardhat") as temp_dir:
        test_case_path = os.path.join(temp_dir, 'test_cases.json')
        with open(test_case_path, 'w') as f:
            json.dump(transactions, f)
        should_record_trace = list(should_record_trace)
        should_record_trace = ['"' + x + '"' for x in should_record_trace]
        js_should_record_trace = F"{','.join(should_record_trace)}"
        
        script_path = os.path.join(temp_dir, 'execute_transactions.js')
        with open(script_path, 'w') as script_file:
            script_file.write(f"""
                const {{ ethers }} = require("hardhat");
                const {{ mine }} = require('@nomicfoundation/hardhat-network-helpers');
                const fs = require("fs");
                const should_include_trace = [{js_should_record_trace}];
                async function executeTransaction(tx) {{               
                    await ethers.provider.send("hardhat_impersonateAccount", [tx.from]);
                    await ethers.provider.send("hardhat_setBalance", [tx.from, "0x3635C9ADC5DEA000000000000000"]);   
                    const signer = await ethers.getSigner(tx.from);
                    let gas = Number(tx.gas)
                    gas = 100000000
                    const currentBlockNumber = await ethers.provider.getBlockNumber();
                    const targetBlockNumber = parseInt(tx.blockNumber, 10);  
                    if (targetBlockNumber && targetBlockNumber > currentBlockNumber) {{
                        const blocksToMine = targetBlockNumber - currentBlockNumber -1;
                        await mine(blocksToMine);
                    }}
                    if (tx.timestamp) {{
                        const timestamp = parseInt(tx.timestamp, 10);  
                        await setNextBlockTimestamp(timestamp);
                    }}
                    
                    let transactionValue;
                    if (tx.value == "0") {{
                        transactionValue = "0";
                    }} else {{
                        const tenEthInWei = ethers.utils.parseUnits("10", "ether"); 
                        const valueInWei = ethers.BigNumber.from(tx.value); 
                        transactionValue = valueInWei.add(tenEthInWei).toString();  
                    }}

                    const transaction = {{
                        to: tx.to || undefined,
                        value: transactionValue,
                        gasLimit: ethers.utils.hexlify(gas),
                        gasPrice: ethers.utils.hexlify(20000000000),
                        data: tx.input
                    }};
                    let txResponse;
                    let txReceipt;
                    let txHash;

                    try {{                        
                        txResponse = await signer.sendTransaction(transaction);       
                        txReceipt = await txResponse.wait();  
                        txHash = txReceipt.transactionHash;
                    }} catch (error) {{               
                        if (error.transactionHash) {{                         
                            txHash = error.transactionHash;                         
                            txReceipt = await ethers.provider.getTransactionReceipt(txHash);
                        }}
                    }}             
                    return {{ hash: txHash, receipt: txReceipt}};
                }}                
                async function main() {{
                const testCasesPath = './test_cases.json';
                const testResultPath = './result.json';
                const testCases = require(testCasesPath);
                let results = {{}};         
                let contractAddr;

                for (let i = 0; i < testCases.length; i++) {{
                    const tx = testCases[i];           
                    if (i === 0) {{
                        const deployResult = await executeTransaction(tx);
                        contractAddr = deployResult.receipt.contractAddress;
                        results = {{
                            receipt: deployResult.receipt,
                            hash: deployResult.hash,
                        }};
                    }} else {{
                        
                        tx.to = contractAddr;
                        const result = await executeTransaction(tx);
                        
                        results = {{
                            receipt: result.receipt,
                            hash: result.hash
                        }};
                    }}
                    if (should_include_trace.includes(tx.hash)){{
                        let trace = {{}}
                        try {{ trace = results.hash ? await ethers.provider.send("debug_traceTransaction", [
                        results.hash, {{ disableStack: true, disableStorage: true}} ]) : null; 
                        }} catch (error) {{                  
                            trace = {{}};
                        }}
                        results['trace'] = trace
                    }}
                        try{{
                            fs.writeFileSync(`./${{tx.hash}}_result.json`, JSON.stringify(results, null, 2));
                        }}  catch (error) {{                       
                            trace = {{}};
                        }}
                    }}
                }}


                main();
                """)

        
        config_path = os.path.join(temp_dir, 'hardhat.config.js')
        with open(config_path, 'w') as config_file:
            config_file.write(f"""
            require("@nomiclabs/hardhat-waffle");
            require("@nomiclabs/hardhat-ethers");

            module.exports = {{
                networks: {{
                    hardhat: {{
            allowUnlimitedContractSize: true,
            blockGasLimit: 1000000000  
        }}
                }},
            }};
            """)

        
        command = 'npx hardhat run execute_transactions.js'
        subprocess.run(command, shell=True, cwd=temp_dir)
        result = {}
        for result_file in os.listdir(temp_dir):
            if 'result' not in result_file:
                continue
            txhash = result_file.split('_result')[0]
            try:
                with open(os.path.join(temp_dir, result_file),'r') as f:
                    result[txhash] = json.load(f)
            except Exception as e:
                continue
        return result

def execute_transactions_with_storage_layout(transactions, layout, should_record_trace = []):
    with tempfile.TemporaryDirectory(dir="./Hardhat") as temp_dir:
        test_case_path = os.path.join(temp_dir, 'test_cases.json')
        with open(test_case_path, 'w') as f:
            json.dump(transactions, f)
        should_record_trace = list(should_record_trace)
        should_record_trace = ['"' + x + '"' for x in should_record_trace]
        js_should_record_trace = F"{','.join(should_record_trace)}"
        
        js_slot_layout = json.dumps(layout, indent=2)

        script_path = os.path.join(temp_dir, 'execute_transactions.js')
        with open("../../Documents/scripts/execute_transaction.js", "r") as file:
            script_content = file.read()
        
        with open(script_path, 'w') as script_file:
            script_file.write(script_content.format(js_slot_layout = js_slot_layout))
        
        config_path = os.path.join(temp_dir, 'hardhat.config.js')
        with open(config_path, 'w') as config_file:
            config_file.write(f"""
            require("@nomiclabs/hardhat-waffle");
            require("@nomiclabs/hardhat-ethers");

            module.exports = {{
                networks: {{
                    hardhat: {{
                        allowUnlimitedContractSize: true,
                        blockGasLimit: 1000000000  
                    }}
                }}
            }};
            """)
        
        command = 'npx hardhat run execute_transactions.js'
        subprocess.run(command, shell=True, cwd=temp_dir)
        result = {}
        for result_file in os.listdir(temp_dir):
            if 'result' not in result_file:
                continue
            txhash = result_file.split('_result')[0]
            try:
                with open(os.path.join(temp_dir, result_file),'r') as f:
                    result[txhash] = json.load(f)
            except Exception as e:
                continue
        return result

def execute_test_cases_in_folder_and_record_trace(test_case_folder, layout):
    print("Executing test cases and saving execution traces to folder", test_case_folder)
    for file in os.listdir(test_case_folder):

        if file.endswith('.json') and file.split('.')[0].isnumeric() and file.split('.')[1] == 'json' :
            test_case_id = file.split('.')[0]
            with open(os.path.join(test_case_folder, file), 'r') as f:
                transactions = json.load(f)
                transaction_hashes = [tx['hash'] for tx in transactions]
                result = execute_transactions_with_storage_layout(transactions, layout, transaction_hashes)
                with open(os.path.join(test_case_folder, test_case_id+"_result.json"), 'w+') as fo:
                    json.dump(result, fo, indent=4)
    
def fetch_and_save_traces(contract_address, contract_id,  args, etherscan_api_key, max_transactions):
    def get_transactiones(api_key, start_block=0, end_block=99999999, page=1, offset=10000, sort='asc'):
        url = f'https://api.etherscan.io/api?module=account&action=txlist&address={contract_address}&startblock={start_block}&endblock={end_block}&page={page}&offset={offset}&sort={sort}&apikey={api_key}'
        response = requests.get(url)
        data = response.json()
        if data['status'] == '1':
            return data['result']
        return []
        
    def get_internal_transactions(contract_address, args):
        if not os.path.exists(os.path.join(args.contract_folder, 'Tx_History', contract_address + '_internal.json')):
            return []
        with open(os.path.join(args.contract_folder, 'Tx_History', contract_address + '_internal.json'), 'r') as f:
            internal_txInfo = json.loads(f.read())
            if not internal_txInfo: return []
            result = []
            for tx in internal_txInfo:
                if tx['trace_address'] == None:
                    continue
                converted_tx = {
                        "blockNumber": tx.get("block_number"),
                        "hash": tx.get("transaction_hash", ""),
                        "transactionIndex": tx.get("transaction_index"),
                        "from": tx.get("from_address", ""),
                        "to": tx.get("to_address", ""),
                        "value": tx.get("value", ""),
                        "gas": tx.get("gas", ""),
                        "isError": "0" if tx.get("error") is None else "1",
                        "input": tx.get("input", ""),
                        "methodId": tx.get("input", "")[:10] if tx.get("input") else "",
                        'trace_address': tx.get("trace_address", ""),
                        "isInternal": True,
                    }
                result.append(converted_tx)
            return result
            
    if not os.path.exists(os.path.join(args.contract_folder, 'Tx_History', contract_id + '_external.json')):
        txInfo = get_transactiones(etherscan_api_key)
        with open(os.path.join(args.contract_folder, 'Tx_History', contract_id + '_external.json'), 'w+') as f:
            json.dump(txInfo, f)
    else:
        with open(os.path.join(args.contract_folder, 'Tx_History', contract_id + '_external.json'), 'r') as f:
            txInfo = json.loads(f.read())

    txInfo = sorted(txInfo, key=lambda tx: (int(tx["blockNumber"]), int(tx["transactionIndex"])))

    tx_hash_counts = {}
    for tx in txInfo:
        tx_hash = tx['hash']
        if 'isInternal' in tx and tx_hash not in tx_hash_counts: 
            tx_hash_counts[tx_hash] = 0
        if 'isInternal' in tx and tx_hash in tx_hash_counts:
            tx['hash'] = f"{tx_hash}_{tx_hash_counts[tx_hash]}"
            tx_hash_counts[tx_hash] += 1
    return txInfo[0:max_transactions]

def extract_storage_layout_with_low_version(solidity_path, version, contract_name):
    with tempfile.TemporaryDirectory(dir="./Hardhat") as temp_dir:
        contracts_dir = os.path.join(temp_dir, "contracts")
        scripts_dir = os.path.join(temp_dir, "scripts")
        os.makedirs(contracts_dir)
        os.makedirs(scripts_dir)

        contract_dst_path = os.path.join(contracts_dir, "TargetContract.sol")
        shutil.copy(solidity_path, contract_dst_path)

        # Write the hardcoded extract script
        with open("../../Documents/scripts/get_layout.js", "r") as file:
            script_content = file.read()
        extract_script_path = os.path.join(scripts_dir, "extract.js")
        with open(extract_script_path, 'w') as f:
            f.write(script_content.format(contract_name=contract_name))

        # Write the hardhat config file
        config_path = os.path.join(temp_dir, 'hardhat.config.js')
        with open(config_path, 'w') as config_file:
            config_file.write(f"""
            module.exports = {{
              solidity: "{version}"
            }};
            """)

        # Compile the contract
        try:
            result = subprocess.run(
                ["npx", "hardhat", "compile"],
                cwd=temp_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
        except subprocess.CalledProcessError as e:
            print(f"Compilation failed: {e.stderr}")

        # Run the extraction script
        try:
            result = subprocess.run(
                ["npx", "hardhat", "run", "scripts/extract.js"],
                cwd=temp_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            print("✅ Extraction complete, result saved in Layout.json")
        except subprocess.CalledProcessError as e:
            print(f"Failed to extract layout: {e.stderr}")

        # Load result
        layout_path = os.path.join(temp_dir, "storageLayout.json")
        with open(layout_path, "r") as f:
            layout = json.load(f)

        return layout

def extract_storage_layout_with_high_version(solidity_path, version, contract_name):
    cmd = [
        "solc", "--combined-json", "storage-layout", solidity_path
    ]
    storage_layout = []
    try:
        subprocess.run(['solc-select', 'use', version], check=True)
        output = subprocess.check_output(cmd).decode("utf-8")
        data = json.loads(output)
        for key in data["contracts"].keys():
            value = data["contracts"][key]
            if key[key.find(":")+1:] == contract_name:
                storages = value["storage-layout"]["storage"]
                for variable in storages:
                    tmp_storage = {}
                    tmp_storage["name"] = variable["label"]
                    tmp_storage["type"] = variable["type"].replace("t_", "").replace(",", " => ")
                    tmp_storage["slot"] = int(variable['slot'])
                    storage_layout.append(tmp_storage)
        print("✅ Extraction complete, result saved in Layout.json")
        return storage_layout
    except subprocess.CalledProcessError as e:
        print(f"Failed to extract layout: {e.stderr}")

def test_replayer_and_recorder(source_contract_file, args):
    '''source_contract_file: contract_name + contract_address +.sol'''
    contract_id = source_contract_file['id']
    contract_addr = source_contract_file['address']
    contract_path = source_contract_file['file']
    contract_version = source_contract_file["Compiler Version"]
    contract_name = source_contract_file["name"]
    print("#"*30, "Augmenting test cases for", contract_id, "#"*30)

    test_case_folder = os.path.join(args.augmentation_folder, f'augmented_test_case_{args.max_transactions}', contract_id)
    if os.path.exists(test_case_folder): return
    txInfo = fetch_and_save_traces(contract_addr, contract_id, args, args.etherscan_api, args.max_transactions)   
    save_test_cases(test_case_folder, txInfo)

    layout_folder = os.path.join(args.augmentation_folder, "layout")
    if not os.path.exists(os.path.join(layout_folder, f"{contract_id}.json")):
        if contract_version[0] == 'v': contract_version = contract_version[1:]
        if contract_version.find('+')!=-1: contract_version = contract_version[0:contract_version.find('+')]
        if contract_version.find('-')!=-1: contract_version = contract_version[0:contract_version.find('-')]

        print(contract_version)
        if contract_version[2] == '8':
            layout = extract_storage_layout_with_high_version(contract_path, contract_version, contract_name)
        else:
            layout = extract_storage_layout_with_low_version(contract_path, contract_version, contract_name)

        with open(os.path.join(layout_folder, f"{contract_id}.json"), "w") as f:
            json.dump(layout, f, indent=4)
    else:
        with open(os.path.join(layout_folder, f"{contract_id}.json"), "r") as f:
            layout = json.load(f)
    
    execute_test_cases_in_folder_and_record_trace(test_case_folder, layout)

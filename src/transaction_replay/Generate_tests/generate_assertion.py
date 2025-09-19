import json
import os
import compile_contract
import pack_test_cases
from eth_utils import event_abi_to_log_topic, encode_hex
from web3 import Web3
from eth_abi import decode

from test_case_augment import execute_test_cases_in_folder_and_record_trace




def get_event_topic_0(event):
    
    event_abi = {
        "name": event.name,
        "type": "event",
        "inputs": []
    }
    for param in event.elems:
        param_abi = {
            "name": param.name,
            "type": str(param.type),
            "indexed": param.indexed
        }
        event_abi["inputs"].append(param_abi)

    
    event_topic_0 = encode_hex(event_abi_to_log_topic(event_abi))
    return event_topic_0



def generate_test_scripts(contract_name, topic2event, abi, selector2func):
    test_case_folder = os.path.join('augmented_test_case', contract_name)
    for test_case in os.listdir(test_case_folder):
        assertions = {}
        transactions = []
        if not 'result' in test_case:
            continue
        with open(os.path.join(test_case_folder, test_case.split('_')[0]+'.json'),'r') as f:
            transactions = json.loads(f.read())
            
        with open(os.path.join(test_case_folder, test_case),'r') as f:
            test_case_result = json.loads(f.read())
            for tx in test_case_result:
                r = generate_assertions_per_tx(test_case_result[tx], topic2event, abi)
                if len(r) > 0:
                    assertions[tx] = r
        script = pack_test_cases.generate_test_script(transactions, assertions)
        with open(os.path.join(test_case_folder, test_case.split('_')[0]+'.test.js'), 'w+') as fo:
            fo.write(script)
            

def generate_test_transactions_and_assertions(contract_name, topic2event, abi, selector2func, args):
    test_case_folder = os.path.join(args.augmentation_folder, 'augmented_test_case', contract_name)
    result = {}
    has_execution_trace = False
    for test_case in os.listdir(test_case_folder):
        if 'result' in test_case:
            has_execution_trace = True
            break
    if not has_execution_trace:
        execute_test_cases_in_folder_and_record_trace(test_case_folder)            
    for test_case in os.listdir(test_case_folder):
        assertions = {}
        transactions = []
        if not 'result' in test_case:
            continue
        test_case_number = test_case.split('_')[0] 
        with open(os.path.join(test_case_folder, test_case.split('_')[0]+'.json'),'r') as f:
            transactions = json.loads(f.read())
            
        with open(os.path.join(test_case_folder, test_case),'r') as f:
            test_case_result = json.loads(f.read())
            for tx in test_case_result:
                r = generate_assertions_per_tx(test_case_result[tx], topic2event, abi, selector2func)
                if len(r) > 0:
                    assertions[tx] = r
        for tx in transactions:
            if tx['hash'] in test_case_result and 'receipt' in test_case_result[tx['hash']] and test_case_result[tx['hash']]['receipt']['status'] == 0 :
                tx['isError'] = "1"
        result[test_case_number] = { "transactions": transactions, "assertions": assertions}
        output_path = os.path.join(test_case_folder, test_case.split('_')[0]+'_assertion.json')
        print(f"Saving test assertion in {output_path}")
        if not os.path.exists(output_path):
            with open(output_path, 'w+') as fo:
                only_method_assertion = []
                for i in result[test_case_number]['assertions']:
                    only_method_assertion.extend([x['method'] for x in result[test_case_number]['assertions'][i]])
                json.dump(only_method_assertion,fo)
        
    return result["0"]

def generate_assertions_per_tx(execution_result, topic2event, abi, selector2func):
    assertions = []
    if 'receipt' in execution_result:
        receipt = execution_result['receipt']
        for event in receipt['logs']: 
            topic = event['topics'][0]
            if topic in topic2event:
                event_name = topic2event[topic].name
                key = {}
                key['interface']={'fragments': abi}
                assertions.append({'method': 'emit', 
                                "args": [key, event_name]})
                try:
                    web3 = Web3()
                    contract = web3.eth.contract(address=receipt['to'], abi=abi)
                    event_attr = getattr(contract.events, event_name)()
                    decoded_log = event_attr.process_log(event)
                    for arg in decoded_log['args']:
                        if isinstance(decoded_log['args'][arg],int) and not isinstance(decoded_log['args'][arg],bool):
                            decoded_log['args'][arg] = hex(decoded_log['args'][arg])
                    assertions.append({'method': 'withArgs', 
                                "args": list(decoded_log['args'].values())})
                except:
                    continue
    else:
        return assertions
    if 'trace' not in execution_result:
        if len(assertions) == 0:
            if receipt['status'] == 1:
                assertions.append(
                    {
                        'method': 'not-reverted',
                        'args': '',
                    }
                )
            else:
                assertions.append(
                    {
                        'method': 'reverted',
                        'args': '',
                    }
                )
        return assertions
    trace = execution_result['trace']
    
                
    if receipt['status'] == 0: 
        if trace['structLogs'][-1]['op'].lower() == 'revert' or trace['structLogs'][-1]['op'].lower() == 'invalid': 
            assertions.append(
                {
                    'method': 'reverted',
                    'args': '',
                }
            )
        else:
            assertions.append(
                {
                    'method': 'gas-related reverted',
                    'args': '',
                }
            )
    if trace['returnValue'] != '' and len(trace['returnValue']) >= 2 and receipt['to'] is not None:
        if not trace['returnValue'].startswith("0x08c379a"): 
            assertions.append({
                'method': 'equal',
                'args': trace['returnValue'][2:],
            })
    if len(assertions)  == 0:
        assertions.append(
            {
                'method': 'not-reverted',
                'args': '',
            }
        )
    return assertions

def get_event_to_topics(contract_slither_instance):
    topic2event = {}
    for event in contract_slither_instance.events: 
        event_topic = get_event_topic_0(event)
        topic2event[event_topic] = event
    return topic2event


def extract_recorded_test_cases(contract_info, selector2func, args):
    source_name = contract_info['name']
    print(source_name)
    _, slither_instances = compile_contract.compile_and_analyze_contract(contract_info['address'], contract_info['file'], args.etherscan_api, contract_info['Compiler Version'])

    contract = slither_instances.get_contract_from_name(source_name)[0]
    topic2event = get_event_to_topics(contract)
    return generate_test_transactions_and_assertions(contract_info['id'], topic2event, contract_info['abi'], selector2func, args)
     



import json
import os
import re

def replace_assertions(tx2assertions):
  '''
  relax 1. revert with custom error => revert
  '''
  for t in tx2assertions:
    assertions = tx2assertions[t]
    for assertion in assertions[0]:
        args = assertion["args"]
        processed_args = []
        for arg in args:
            if isinstance(arg, str) and arg.startswith("<SignerWithAddress"):
                address = re.search(r"0x[a-fA-F0-9]+", arg).group()
                processed_args.append(address)
            else:
                processed_args.append(arg)
        assertion['args'] = processed_args
    for idx in range(0,len(assertions[0])-1):
        method = assertions[0][idx]['method']
        if method == 'revertedWithCustomError':
            assertions[0][idx]['method'] = 'reverted'
            assertions[0].pop(idx+1)


  return tx2assertions

def replace_contract_bytecode(transactions, new_bytecode):
    for idx in range(0,len(transactions)):
        if 'to' not in transactions[idx]: 
            transactions[idx]['data'] = '0x'+new_bytecode 
    return transactions

def generate_test_script(transactions, assertions):
    test_script = f"""const {{ expect }} = require("chai");
require("@nomiclabs/hardhat-ethers");
const {{ ethers }} = require('hardhat');
const {{ Contract }} = require("ethers");
const {{ mine }} = require('@nomicfoundation/hardhat-network-helpers');
require("@nomicfoundation/hardhat-chai-matchers");
const path = require('path');
const fs = require('fs');

function saveTrace(txHash, trace) {{
    const traceDir = path.join(__dirname, '..', 'trace');
    if (!fs.existsSync(traceDir)) {{
        fs.mkdirSync(traceDir, {{ recursive: true }});
    }}
    const filePath = path.join(traceDir, `${{txHash}}.json`);
    fs.writeFileSync(filePath, JSON.stringify(trace, null, 2));
}}


describe("test", function () {{
  it("Should execute all transactions", async function () {{
    let contractAddress = undefined;
    let results = [];  

    for (const tx of transactions) {{
      let txResultEntry = {{ hash: tx.hash, pass_assertion: false, revert: false, revert_reason: '', failed_assertion: [], checked_assertion: [], assertion_fail_reason: ''}};
      if (tx.from) {{
        await network.provider.request({{
          method: "hardhat_impersonateAccount",
          params: [tx.from],
        }});
        await ethers.provider.send("hardhat_setBalance", [tx.from, "0x3635C9ADC5DEA000000000000000"]);  
      }}
      
      

      const signer = await ethers.getSigner(tx.from);
      let gas = Number(tx.gas)
      if (tx.isError == '0') {{
          gas = gas + 10000000
      }}
      const transaction = {{
          to: contractAddress,
          value: tx.value, 
          gasLimit: 90000000,
          gasPrice: 8000000000,
          data: tx.input
      }};          
      
      
        let txResult;
        let txHash;
        let txReceipt;

        try {{
            
            txResult =  signer.sendTransaction(transaction);
            txHash = (await txResult).hash
            txReceipt = await (await txResult).wait();  
            if (txReceipt.contractAddress) {{
              contractAddress = txReceipt.contractAddress
              
            }}
            
            
            
            
            
              txResultEntry.revert = false;
              

        }} catch (error) {{
            txResultEntry.revert = true;
            txResultEntry.revert_reason = error.message;
            if (error.transactionHash) {{
                
                txHash = error.transactionHash;
                
                txReceipt = await ethers.provider.getTransactionReceipt(txHash);
            }}
            
        }}
        let trace;
        if (txHash) {{
          trace = await network.provider.send("debug_traceTransaction", [txHash]);
          
        }}
        
        
        if (assertions[tx.hash]) {{
          let assertionChain = expect(txResult);
          let contract;
          try{{
          for (const assertion of assertions[tx.hash]) {{
              txResultEntry.checked_assertion.push(assertion['method'])
              
              switch (assertion['method']) {{
                  case "revertedWithCustomError":
                      contract = new Contract(contractAddress, assertion.args[0]['interface']['fragments'], signer);
                      assertionChain = assertionChain.to.be.revertedWithCustomError(contract, assertion.args[1]);
                      break;
                  case "revertedWithPanic":
                      assertionChain = assertionChain.to.be.revertedWithCustomError(...assertion.args);
                      break;
                  case "reverted":
                      assertionChain = assertionChain.to.be.reverted;
                      break;
                  case "not-reverted":
                      assertionChain = assertionChain.to.not.be.reverted;
                      break;
                  case "equal":
                      expect(trace['returnValue']).to.equal(assertion.args);
                      break;
                  case "changeTokenBalance":
                      contract = new Contract(contractAddress, assertion.args[0]['interface']['fragments'], signer);
                      assertionChain = assertionChain.to.changeTokenBalance(contract, assertion.args[1], assertion.args[2]);
                      break;
                  case "withArgs":
                      assertionChain = assertionChain.withArgs(...assertion.args);
                      break;
                  case "emit":
                    contract = new Contract(contractAddress, assertion.args[0]['interface']['fragments'], signer);
                      assertionChain = assertionChain.to.emit(contract, assertion.args[1]);
                      break;
                  case "not-emit":
                      contract = new Contract(contractAddress, assertion.args[0]['interface']['fragments'], signer);
                      assertionChain = assertionChain.to.not.emit(contract, assertion.args[1]);
                      break;
                  default:
                    
                    break;
                  
                }}
            }}
          await assertionChain;
          txResultEntry.pass_assertion = true;
          }} catch(error) {{
              for (const assertion of assertions[tx.hash]) {{
                if (assertion['method']=='emit'){{
                  assertion['args'].shift()
                }}
                txResultEntry.failed_assertion.push(assertion)
              }}
              txResultEntry.assertion_fail_reason = error.message;
          }}
          results.push(txResultEntry);

          }}
    

    }}
    let success = true;
    for (const result of results) {{
        if (result.pass_assertion){{
          continue
        }} else{{
          success = false;
        }}
    }}
    let partial_success = results[results.length - 1].pass_assertion;

    let fileName = ''
    if (success) {{
    
    fileName = path.basename(__filename, path.extname(__filename)) + ".success" + ".json";
    }} else if (partial_success) {{
      fileName = path.basename(__filename, path.extname(__filename)) + ".partial_success" +  ".json";
    }} else {{
      fileName = path.basename(__filename, path.extname(__filename)) + ".fail" + ".json";
    }}
    const filePath = path.join(__dirname, fileName);
    fs.writeFileSync(filePath, JSON.stringify(results, null, 2));
  }});
}});

const transactions = {json.dumps(transactions, indent=2)}
const assertions = {json.dumps(assertions, indent=2)}
"""

    return test_script
  
  
def pack_test_cases_to_folder(test_case_folder, testcases):
  
    if not os.path.exists(test_case_folder):
        os.makedirs(test_case_folder)
    scripts = generate_test_script(testcases['transactions'], testcases['assertions'])
    with open(os.path.join(test_case_folder, '0.test.js'), 'w+') as f:
        f.write(scripts)


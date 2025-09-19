const {{ ethers }} = require("hardhat");
const {{ mine, setNextBlockTimestamp }} = require('@nomicfoundation/hardhat-network-helpers');
const fs = require("fs");
const crypto = require("crypto");

const slotLayout = {js_slot_layout};

function collectAddresses(tx) {{
  const activeAddresses = new Set();
  if (tx.from) activeAddresses.add(tx.from.toLowerCase());
  if (tx.to) activeAddresses.add(tx.to.toLowerCase());
  return activeAddresses;
}}

async function readContractState(contractAddr, watchedAddresses, slotLayout) {{
  const state = {{}};
  const mappingSlots = {{}};
  
  for (const entry of slotLayout) {{
    const {{ slot, name, type }} = entry;
    if (type.startsWith("mapping")) {{
      mappingSlots[name] = slot;
    }} else {{
      const value = await ethers.provider.getStorageAt(contractAddr, slot);
      state[name] = value;
    }}
  }}
  for (const name in mappingSlots) {{
    const slot = mappingSlots[name];
    const mappingState = {{}};
  
    for (const addr of watchedAddresses) {{
      if (slotLayout.find(e => e.name === name).type.includes("mapping(address => mapping")) {{
        for (const spender of watchedAddresses) {{
          const paddedOwner = ethers.utils.hexZeroPad(addr, 32);
          const paddedSlot = ethers.utils.hexZeroPad(ethers.utils.hexlify(slot), 32);
          const innerSlot = ethers.utils.keccak256(paddedOwner + paddedSlot.slice(2));
          const paddedSpender = ethers.utils.hexZeroPad(spender, 32);
          const finalSlot = ethers.utils.keccak256(paddedSpender + innerSlot.slice(2));
          const value = await ethers.provider.getStorageAt(contractAddr, finalSlot);
          mappingState[`${{addr}}_${{spender}}`] = value;
        }}
      }} else {{
        const paddedKey = ethers.utils.hexZeroPad(addr, 32);
        const paddedSlot = ethers.utils.hexZeroPad(ethers.utils.hexlify(slot), 32);
        const finalSlot = ethers.utils.keccak256(paddedKey + paddedSlot.slice(2));
        const value = await ethers.provider.getStorageAt(contractAddr, finalSlot);
        mappingState[addr] = value;
      }}
    }}
  
    const hash = crypto.createHash('sha256').update(JSON.stringify(mappingState)).digest('hex');
    state[`${{name}}_digest`] = hash;
    state[`${{name}}_raw`] = mappingState;
  }}
  
  return state;
}}

async function executeTransaction(tx) {{
  await ethers.provider.send("hardhat_impersonateAccount", [tx.from]);
  await ethers.provider.send("hardhat_setBalance", [tx.from, "0x3635C9ADC5DEA000000000000000"]);
  const signer = await ethers.getSigner(tx.from);
  let gas = 100000000;
  const currentBlockNumber = await ethers.provider.getBlockNumber();
  const targetBlockNumber = parseInt(tx.blockNumber, 10);

  if (targetBlockNumber && targetBlockNumber > currentBlockNumber) {{
    const blocksToMine = targetBlockNumber - currentBlockNumber - 1;
    await mine(blocksToMine);
  }}

  if (tx.timestamp) {{
    const timestamp = parseInt(tx.timestamp, 10);
    await setNextBlockTimestamp(timestamp);
  }}

  let transactionValue;
  if (tx.value === "0" || tx.value === 0) {{
    transactionValue = ethers.BigNumber.from(0);
  }} else {{
    const tenEthInWei = ethers.utils.parseUnits("10", "ether");
    const valueInWei = ethers.BigNumber.from(tx.value);
    transactionValue = valueInWei.add(tenEthInWei);
  }}

  const transaction = {{
    to: tx.to || undefined,
    value: transactionValue, 
    gasLimit: ethers.BigNumber.from(gas),
    gasPrice: ethers.BigNumber.from(20000000000),
    data: tx.input
  }};

  let txResponse, txReceipt, txHash;
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

  return {{ hash: txHash, receipt: txReceipt }};
}}

async function main() {{
  const testCasesPath = './test_cases.json';
  const testCases = require(testCasesPath);
  let results = {{}};
  let contractAddr;

  for (let i = 0; i < testCases.length; i++) {{
    const tx = testCases[i];
    const activeAddresses = collectAddresses(tx);
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

    let trace = {{}}
    try {{ 
        const fullTrace = await ethers.provider.send("debug_traceTransaction", [
        results.hash, {{ disableStack: true, disableStorage: true }}]);
        trace = {{
          failed: fullTrace.failed,
          gas: fullTrace.gas,
          returnValue: fullTrace.returnValue
        }};
    }} catch (error) {{                  
        trace = {{}};
    }}
    results['trace'] = trace;

    const watchedAddresses = Array.from(activeAddresses);
    if (contractAddr) {{
      const state = await readContractState(contractAddr, watchedAddresses, slotLayout);
      results['state'] = state;
    }}

    const logs = results.receipt?.logs?.map(log => ({{
      address: log.address,
      topics: log.topics,
      data: log.data
    }})) || [];
    results['logs'] = logs;

    try {{
      fs.writeFileSync(`./${{tx.hash || `tx_${{i}}`}}_result.json`, JSON.stringify(results, null, 2));
    }} catch (error) {{
      console.error(error);
    }}
  }}
}}

main()
  .then(() => process.exit(0))
  .catch(() => process.exit(1));
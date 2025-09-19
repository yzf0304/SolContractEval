











const fs = require('fs');
const path = require('path');

const { argv } = require('yargs/yargs')()
  .env('')
  .options({
    
    compiler: {
      alias: 'compileVersion',
      type: 'string',
      default: '0.8.20',
    },
    src: {
      alias: 'source',
      type: 'string',
      default: 'contracts',
    },
    mode: {
      alias: 'compileMode',
      type: 'string',
      choices: ['production', 'development'],
      default: 'development',
    },
    ir: {
      alias: 'enableIR',
      type: 'boolean',
      default: false,
    },
    
    coverage: {
      type: 'boolean',
      default: false,
    },
    gas: {
      alias: 'enableGasReport',
      type: 'boolean',
      default: false,
    },
    coinmarketcap: {
      alias: 'coinmarketcapApiKey',
      type: 'string',
    },
  });

require('@nomicfoundation/hardhat-chai-matchers');
require('@nomicfoundation/hardhat-ethers');
require('hardhat-exposed');
require('hardhat-ignore-warnings');





const withOptimizations = argv.gas || argv.coverage || argv.compileMode === 'production';
const allowUnlimitedContractSize = argv.gas || argv.coverage || argv.compileMode === 'development';


const { ethers } = require("ethers");
const crypto = require('crypto');

let transactionAssertions = [];
let suiteStack = [];
let suiteSetUpTransactions = {}; 
let currentTransactionHash = null;
let currentCall = null;
let callCounter = 0;
let currentTestTitle = '';
let currentTestSuite = '';
let isInitialSuiteSetUp = false
let isRepeatingSuiteSetUp = false;
let lastIsCallOrTx = 0; 
let isExpecting = false

async function calculateTransactionHash(tx) {
  const txData = {
      to: tx.to,
      data: tx.data,
      gasLimit: ethers.BigNumber.from(tx.gas),
      nonce: await ethers.provider.getTransactionCount(tx.from, 'latest'),
      gasPrice: await ethers.provider.getGasPrice(),
      chainId: (await ethers.provider.getNetwork()).chainId
  };

  const signedTx = await ethers.provider.getSigner(tx.from).signTransaction(txData);
  const txHash = ethers.utils.keccak256(signedTx);
  return txHash;
}


extendEnvironment((hre) => {
  
  const originalSend = hre.network.provider.send.bind(hre.network.provider);
  const { ethers } = require("ethers");

  
  hre.network.provider.send = async (method, params) => {
    if (method === 'eth_sendTransaction') {
      const txId = crypto.createHash('sha256').update(JSON.stringify(params) + callCounter++).digest('hex');
      const blockNumber = await hre.ethers.provider.getBlockNumber();
      currentTransactionHash = txId;

      lastIsCallOrTx = 1

      let recordParams = {}
      recordParams['block'] = blockNumber
      recordParams['hash'] = txId
      recordParams['from'] = params[0]['from']
      recordParams['to'] = params[0]['to']
      recordParams['data'] = params[0]['data']
      recordParams['nonce'] = params[0]['nonce']

      const transactionData = `${JSON.stringify(recordParams, null)}\n`;
      if (!isInitialSuiteSetUp && !isRepeatingSuiteSetUp ) {
        console.log('Recording Transaction:', txId);
        fs.appendFileSync(path.join(__dirname,"test_recorder", currentTestTitle, 'transactions.log'), transactionData);
      }
      else if (isInitialSuiteSetUp){
        suiteSetUpTransactions[currentTestSuite].push(transactionData)
        console.log('Suite Init Transaction:', currentTransactionHash);
      }
      return originalSend('eth_sendTransaction', params);
    }
    else if (method === 'eth_call') {
      
      const blockNumber = await hre.ethers.provider.getBlockNumber();

      const callId = crypto.createHash('sha256').update(JSON.stringify(params[0]) + callCounter++).digest('hex');

       
      if (!isExpecting) {
        currentCall = callId
      }

      let recordParams = {}
      recordParams['block'] = blockNumber
      recordParams['hash'] = callId
      recordParams['from'] = params[0]['from']
      recordParams['to'] = params[0]['to']
      recordParams['data'] = params[0]['data']
      recordParams['isCall'] = true

      lastIsCallOrTx = 0


      const callData = `${JSON.stringify(recordParams, null)}\n`;
      if (!isInitialSuiteSetUp && !isRepeatingSuiteSetUp ) {
        console.log('Recording Current Call:', callId);
        fs.appendFileSync(path.join(__dirname,"test_recorder", currentTestTitle, 'transactions.log'), callData);
      }
      else if (isInitialSuiteSetUp) {
        suiteSetUpTransactions[currentTestSuite].push(callData)
        console.log('Suite Init Call:', callId);
      }
      return originalSend('eth_call', params);
    }
    return originalSend(method, params);
  };
});

const chai = require("chai");
const {Assertion } = chai;
const originalExpect = chai.expect;

chai.expect = (...args) => {
  isExpecting = true
  
  return originalExpect(...args);
};



Object.keys(Assertion.prototype).forEach(method => {
  if (typeof Assertion.prototype[method] === 'function') {
    const originalMethod = Assertion.prototype[method];
    Assertion.prototype[method] = function (...args) {
      if (this.__flags.negate) {
        console.log("Checking Assertion", "not-" + method, currentCall, currentTransactionHash);

        transactionAssertions.push({"method": "not-" + method, args});
      } else {
        transactionAssertions.push({method, args});
        console.log("Checking Assertion", method, currentCall, currentTransactionHash);
      }
      const result = originalMethod.apply(this, args);

      if (["changeTokenBalances","changeTokenBalance", "revertedWithPanic"].includes(method)) {
        record_assertion();
      }   

      return result;
    };
  }
});

const Mocha = require('mocha');
const { Spec } = Mocha.reporters;
class CustomReporter extends Spec {
  constructor(runner) {
    runner.on('suite', (suite) => {
      currentTransactionHash = null;
      currentCall = null;
      currentTestSuite = suite.title.replace(/\s/g, '_');
      suiteStack.push(currentTestSuite)
      if (!(currentTestSuite in suiteSetUpTransactions)){
        suiteSetUpTransactions[currentTestSuite] = []
      }
      
    });

    runner.on('suite end', (suite) => {
      
      suiteStack.pop()
      if (currentTestSuite.length >=1){
        currentTestSuite = suiteStack[suiteStack.length - 1]
      } else {
        currentTestSuite = null
      }
    });

    runner.on('test', (test) => {
      currentTestTitle = path.join(...suiteStack, test.title.replace(/\s/g, '_')) 
      transactionAssertions = []
      callCounter = 0;

      const logFilePath = path.join(__dirname, "test_recorder", currentTestTitle)
      if (fs.existsSync(logFilePath)) {
        
        fs.rmSync(logFilePath, { recursive: true, force: true });
      }
      
      fs.mkdirSync(logFilePath, { recursive: true });
    

      console.log(`Entering Test Case ${currentTestTitle}`);
    });

    runner.on('test end', (test) => {
      suiteStack.forEach((suite) => {
        suiteSetUpTransactions[suite].forEach((transaction) => {
          fs.appendFileSync(path.join(__dirname,"test_recorder", currentTestTitle, 'init.log'), transaction);
        });
      });
    });

    runner.on('hook', (hook) => {
      
      if (hook.title.includes('before each')) {
        let par =  hook.parent.title.replace(/\s/g, '_');
        if (suiteSetUpTransactions[currentTestSuite].length == 0 && (par == currentTestSuite || suiteSetUpTransactions[par].length ==0)){
          isInitialSuiteSetUp = true;
          isRepeatingSuiteSetUp = false;
          console.log("Inside Suite:", par, "Current Testing is", currentTestSuite)
        } else{
          isRepeatingSuiteSetUp = true;
          isInitialSuiteSetUp = false;
        }
        
      }
    });

    runner.on('hook end', (hook) => {
      if (hook.title.includes('before each')) {
        isInitialSuiteSetUp = false
        isRepeatingSuiteSetUp = false
        
      }
    });

    super(runner);

  }
}


function record_assertion() {
  tx2assert = {};
  if (currentCall != null && currentTransactionHash == null) {
    tx2assert = {
      "currentTransactionHash": currentCall,
      'asserts': transactionAssertions,
    };
  } else if (currentCall == null && currentTransactionHash != null) {
    tx2assert = {
      "currentTransactionHash": currentTransactionHash,
      'asserts': transactionAssertions,
    };
  } else if (currentCall == null && currentTransactionHash == null) {
    tx2assert = {};
    console.log("Warning: Nothing in expect");
  } else {
    if (lastIsCallOrTx == 0) {
      tx2assert = {
        "currentTransactionHash": currentCall,
        'asserts': transactionAssertions,
      };
    } else {
      tx2assert = {
        "currentTransactionHash": currentTransactionHash,
        'asserts': transactionAssertions,
      };
    }
  }

  if (Object.keys(tx2assert).length != 0){
    console.log("Recording Assertion")
    const message = `${JSON.stringify(tx2assert, (key, value) => {
      
      if (typeof value === 'bigint') {
        return value.toString();
      } else if (value === null){
        return undefined
      }
      return value;
    })}\n`;
  const logFilePath = path.join(__dirname, "test_recorder", currentTestTitle, 'assertions.log');
  fs.appendFileSync(logFilePath, message);
}
}

const originalAssert = chai.Assertion.prototype.assert;
chai.Assertion.prototype.assert = function (...args) {
  transactionAssertions.push({method: this, args});
  originalAssert.apply(this, args);
  record_assertion();

  currentCall = null;
  currenTransactionHash = null;
  transactionAssertions = []
  isExpecting = false
};


/**
 * @type import('hardhat/config').HardhatUserConfig
 */
module.exports = {
  solidity: {
    version: argv.compiler,
    settings: {
      optimizer: {
        enabled: withOptimizations,
        runs: 200,
      },
      viaIR: withOptimizations && argv.ir,
      outputSelection: { '*': { '*': ['storageLayout'] } },
    },
  },
  warnings: {
    'contracts-exposed/**/*': {
      'code-size': 'off',
      'initcode-size': 'off',
    },
    '*': {
      'code-size': withOptimizations,
      'unused-param': !argv.coverage, 
      default: 'error',
    },
  },
  networks: {
    hardhat: {
      allowUnlimitedContractSize,
      initialBaseFeePerGas: argv.coverage ? 0 : undefined,
      blockGasLimit: 100000000,
    },
  },
  exposed: {
    imports: true,
    initializers: true,
    exclude: ['vendor/**/*', '**/*WithInit.sol'],
  },
  gasReporter: {
    enabled: argv.gas,
    showMethodSig: true,
    currency: 'USD',
    coinmarketcap: argv.coinmarketcap,
  },
  paths: {
    sources: argv.src,
  },
  mocha: {
    reporter: CustomReporter,
  },
};


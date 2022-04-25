//import *  as Keychain from '@stacks/keychain';
import { getEnv } from './config';
import * as Transaction from '@stacks/transactions';
import { StacksMainnet, StacksMocknet, StacksTestnet } from '@stacks/network';
import { decryptPrivateKey, makeDIDFromAddress } from '@stacks/auth';
import { Buffer } from 'buffer';
import { ecPairToAddress, getPublicKeyFromPrivate, makeECPrivateKey, publicKeyToAddress } from '@stacks/encryption';
import {
    createWalletGaiaConfig,
    generateNewAccount,
    generateSecretKey,
    generateWallet,
    restoreWalletAccounts,
    updateWalletConfig,
    getStxAddress,
    getGaiaAddress,
    decrypt as decryptMnemonic,
    encrypt as encryptMnemonic,
} from '@stacks/wallet-sdk';
import {
    getAbi,
    callReadOnlyFunction,
    makeSTXTokenTransfer,
    makeContractDeploy,
    makeContractCall,
    makeStandardSTXPostCondition,
    broadcastTransaction,
    deserializeTransaction,
    BufferReader,
    pubKeyfromPrivKey as stkPubKeyFromPrivKey,
    getAddressFromPublicKey,
    createStacksPrivateKey,
    TransactionVersion,
} from '@stacks/transactions';

import {
    someCV, intCV, trueCV, noneCV
    , falseCV, uintCV, listCV, bufferCV, standardPrincipalCV
    , bufferCVFromString, serializeCV, contractPrincipalCV
    , encodeClarityValue, ListCV
} from '@stacks/transactions';
import { principalCV } from '@stacks/transactions/dist/clarity/types/principalCV';

const BigNum = require('bn.js');

// check balance
// curl -s https://stacks-node-api.testnet.stacks.co/extended/v1/address/ST3KG5NBY7ABBT1879Q0MCPK3M7YJZHFWJBF9KHKY/balances
// curl -s https://stacks-node-api.testnet.stacks.co/extended/v1/tx/0x7275982c6f6f69197befc83f6a4bd2423ea515883fb218dcecea417d40c035d8
// faucet(testnet/regtest only)
// curl -s curl https://stacks-node-api.regtest.stacks.co/extended/v1/faucets/stx?address=ST1FA989QSTTKYM4R0H14NGP2TP6FDDKP6CTAWAPG -X POST
// download source
// curl -s 'https://stacks-node-api.mainnet.stacks.co/v2/contracts/source/ST3KG5NBY7ABBT1879Q0MCPK3M7YJZHFWJBF9KHKY/Artie' | jq -r .source

export { decrypt as decryptMnemonic, encrypt as encryptMnemonic } from '@stacks/wallet-sdk';
export { getAbi } from '@stacks/transactions';

export class CustomTestNet extends StacksTestnet {
    constructor(coreApiUrl) {
        super('https://stacks-node-api.testnet.stacks.co')
        //    this.coreApiUrl = coreApiUrl || 'https://stacks-node-api.regtest.stacks.co';
        //    this.coreApiUrl = coreApiUrl || 'https://stacks-node-api.testnet.stacks.co';
    }
}

export class CustomMainNet extends StacksMainnet {
    constructor(coreApiUrl) {
        super();
        this.coreApiUrl = coreApiUrl || this.coreApiUrl;
    }
}

export class CustomMockNet extends StacksMocknet {
    constructor(coreApiUrl) {
        super(coreApiUrl || this.coreApiUrl);
    }
}


export async function createWallet(mnemonic, password) {

    mnemonic = mnemonic || generateSecretKey(256);
    password = password || 'password';
    const _wallet = await generateWallet({
        secretKey: mnemonic,
        password: password,
    });
    const publicAddresses = getPublicAddresses(_wallet, 0);
    return {
        mnemonic: (await encryptMnemonic(mnemonic, password)).toString('hex')
        , password
        , _wallet
        , stxPubAddressSP: publicAddresses.stxAddress.mainnet
        , stxPubAddressST: publicAddresses.stxAddress.testnet
    };
}

export function getPublicAddresses(wallet, idx) {
    const account = wallet.accounts[idx || 0];
    // this is the 'gaia' public address(btc format)
    const gaiaAddress = getGaiaAddress(account);
    const publicKey = getPublicKeyFromPrivate(account.dataPrivateKey);
    // btc address, 1XXXXX, shown in explorer
    const address = publicKeyToAddress(publicKey);
    const referenceDID = makeDIDFromAddress(address);
    // STX address (only SP/ST prefix difference)
    const stxAddressSP = getStxAddress({
        account: wallet.accounts[0],
        transactionVersion: Transaction.TransactionVersion.Mainnet
    });
    const stxAddressST = getStxAddress({
        account: wallet.accounts[0],
        transactionVersion: Transaction.TransactionVersion.Testnet
    });
    // different construction for STX public key
    //const stxPublicKey = stkPubKeyFromPrivKey(account.stxPrivateKey);
    const stxPublicKey = getPublicKeyFromPrivate(account.stxPrivateKey.slice(0, 64));
    //const stxPubAddress = getAddressFromPublicKey(stxPublicKey.data);
    const stxPubAddressSP = getAddressFromPublicKey(stxPublicKey, TransactionVersion.Mainnet);
    const stxPubAddressST = getAddressFromPublicKey(stxPublicKey, TransactionVersion.Testnet);
    return {
        stxAddress: {
            mainnet: stxAddressSP,
            testnet: stxAddressST,
        },
        gaiaAddress: gaiaAddress,
        referenceDID: referenceDID,
    }
}
export let sampleWallet = null;
export let nodeWallet = null;

let cachedAbi = {

}
const RegTestNetwork = new CustomTestNet();

function identity(x) { return x; };

function getTxAccount(wallet, idx) {
    const txWallet = wallet || sampleWallet;
    const account = txWallet.accounts[idx];
    const privateKey = account.stxPrivateKey;
    const publicAdresses = getPublicAddresses(txWallet, idx);
    return {
        publicAdresses, privateKey
    };
}
function convertFunctionParams(abi, values) {
    return abi.args.map((p, i) => {
        const v = values[i];
        if (p.type === 'principal') {
            return v == undefined || v == null ? noneCV() : principalCV(values[i]);
        }
        if (/^uint/.test(p.type)) {
            return v == undefined || v == null ? noneCV() : uintCV(values[i]);
        }
        if (/^int/.test(p.type)) {
            return v == undefined || v == null ? noneCV() : intCV(values[i]);
        }
        else if (p.type === 'string') {
            return v == undefined || v == null ? noneCV() : bufferCVFromString(values[i]);
        }
        else return noneCV();
    });
}
export async function getContractAbi(owner, contractName, network = RegTestNetwork) {
    // probably should use some memoize lib
    const coreApiUrl = network.coreApiUrl;
    let networkCached = cachedAbi[coreApiUrl];
    if (!networkCached) {
        networkCached = cachedAbi[coreApiUrl] = {};
    }
    let cachedOwner = networkCached[owner];
    if (!cachedOwner) {
        cachedOwner = networkCached[owner] = {};
    }
    let abi = cachedOwner[contractName];
    if (!abi) {
        abi = await getAbi(owner, contractName, network);
        cachedOwner[contractName] = abi;
    }
    return abi;
}

export async function signSmartContract(clarityCode, contractName, wallet = sampleWallet, accountIndex = 0, network = RegTestNetwork, transformContract = identity) {
    const { privateKey, publicAdresses } = getTxAccount(wallet, accountIndex);
    const txOptions = {
        contractName: contractName,
        codeBody: transformContract(clarityCode, { publicAdresses, network }),
        senderKey: privateKey,
        network,
    };

    const transaction = await makeContractDeploy(txOptions);
    return transaction.serialize().toString('hex');
}

export async function signContractCall(contractAdress, functionName, paramAbi = [], params = [], wallet = sampleWallet, accountIndex = 0, network = RegTestNetwork) {
    const { privateKey, publicAdresses } = getTxAccount(wallet, accountIndex);
    const [owner, contractName] = contractAdress.split('.');
    const abi = await getContractAbi(owner, contractName, network);
    const postConditions = [];
    const txOptions = {
        contractAddress: owner,
        contractName: contractName,
        functionName: functionName,
        functionArgs: convertFunctionParams(paramAbi, params),
        senderKey: privateKey,
        validateWithAbi: true,
        network,
        postConditions,
    };
    const transaction = await makeContractCall(txOptions);
    const serializedTxHex = transaction.serialize().toString('hex');
    const bufferReader = new BufferReader(Buffer.from(serializedTxHex));
    const deserializedTx = deserializeTransaction(bufferReader);
    return serializedTxHex;
}

export async function makeReadOnlyContractCall(contractAdress, functionName, contractAbi = {}, params = [], wallet = sampleWallet, accountIndex = 0, network = RegTestNetwork) {
    const { privateKey, publicAdresses } = getTxAccount(wallet, accountIndex);
    const [owner, contractName] = contractAdress.split('.');
    const abi = await getContractAbi(owner, contractName, network);
    const functionAbi = ((contractAbi || {}).functions || []).filter(f => f.name === functionName)[0];
    const txOptions = {
        contractAddress: owner,
        contractName: contractName,
        functionName: functionName,
        functionArgs: convertFunctionParams(functionAbi, params),
        senderAddress: publicAdresses.stxAddress,
        validateWithAbi: true,
        network,
    };
    const result = await callReadOnlyFunction(txOptions);
    return result;
}

export async function loadWallet() {
    const secret = getEnv('NODE_SECRET');
    const password = getEnv('NODE_PASSWORD');
    if (secret && password) {
        const b = Buffer.from(secret.replace(/^0x/, ''), "hex");
        const mnemonic = await decryptMnemonic(b, password);
        const wallet = await createWallet(mnemonic, password);
        const { stxPubAddressSP, stxPubAddressST } = wallet;
        console.log(`node wallet: ${stxPubAddressSP}, ${stxPubAddressST}`);
        nodeWallet = wallet;
    }
    else {
        await createWallet(undefined, password || "abcd")
            .then(wallet => {
                sampleWallet = wallet;
                const { stxPubAddressSP, stxPubAddressST, mnemonic } = wallet;
                console.log(`sample wallet: ${stxPubAddressSP}, ${stxPubAddressST} ${mnemonic}`);
            })
            .catch(err => {
                console.log(`error creating sample Wallet ${err}`);
            });

        nodeWallet = sampleWallet;
        console.log(`node wallet is sample wallet ${nodeWallet}`);
    }
}

export function getNodeWallet() {
    return nodeWallet;
}


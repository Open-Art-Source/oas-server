import { getEnv, getMarketContract, getNftContract, getFtContract, getNetworkObject } from './config';
import { StacksTestnet, StacksMainnet } from '@stacks/network';
//import raw from "raw.macro";
import { readFile } from 'fs';
import {
    uintCV,
    intCV,
    bufferCV,
    stringAsciiCV,
    stringUtf8CV,
    standardPrincipalCV,
    trueCV,
    contractPrincipalCV,
    listCV,
    FungibleConditionCode,
    NonFungibleConditionCode,
    noneCV,
    AuthType,
    createAssetInfo,
    makeStandardNonFungiblePostCondition, makeContractFungiblePostCondition, makeStandardSTXPostCondition,
    createSTXPostCondition, createFungiblePostCondition, createNonFungiblePostCondition,
    makeContractCall, makeContractDeploy, makeSTXTokenTransfer,
    AnchorMode,
    PostConditionMode,
    TransactionVersion,
    broadcastTransaction, broadcastRawTransaction, contractPrincipalCVFromAddress,
    deserializeTransaction, sponsorTransaction, BufferReader,
    getNonce,
    estimateContractFunctionCall, estimateTransfer, estimateContractDeploy,
    callReadOnlyFunction,
    PayloadType,
    cvToJSON,
    makeContractSTXPostCondition,
    makeContractNonFungiblePostCondition,
    makeUnsignedContractCall, makeUnsignedSTXTokenTransfer,
    getAbi, getAddressFromPublicKey, addressFromVersionHash, addressFromHashMode, addressToString,
    TransactionSigner, createStacksPrivateKey
} from '@stacks/transactions';
import { createWallet, getContractAbi, getNodeWallet } from './wallet';
import BigNum from 'bn.js';
import { makeStandardFungiblePostCondition } from '@stacks/transactions';
import { principalCV } from '@stacks/transactions/dist/clarity/types/principalCV';
import { AddressHashMode } from '@blockstack/stacks-transactions';
import { ChainID } from '@stacks/common';

function identity(x) { return x; };
function isTrue(x) { return !!(x && (x === 'true' || x === 'yes' || x === '1')); }
function isFalse(x) { return !!(x && (x === 'false' || x === 'no' || x === '0')); }

const sponsoredMode = isTrue(getEnv('SPONSORED'));
const validateWithAbi = !isFalse(getEnv('VALIDATE_WITH_ABI'));
let booster = BigInt(getEnv('SPEED_BOOSTER') || 1);

console.log(`sponsored mode ${sponsoredMode} validate abi: ${validateWithAbi} booster: ${booster}`);
let sponsorStepper = BigInt(1);
let nextSponsorNonce = undefined;

export function broadcastSponsoredTransaction(serializedTx, networkObject, txFee) {
    const bufferReader = new BufferReader(Buffer.from(serializedTx, 'hex'));
    const deserializedTx = deserializeTransaction(bufferReader);
    const sponsorKey = getNodeWallet()._wallet.accounts[0].stxPrivateKey;
    const fee = txFee;
    const sponsorOptions = {
        transaction: deserializedTx,
        sponsorPrivateKey: sponsorKey.replace(/^0x/, ''),
        network: networkObject,
        fee: (fee * (booster + sponsorStepper)) || undefined,
        sponsorNonce: nextSponsorNonce,
    };
    nextSponsorNonce = undefined;
    return sponsorTransaction(sponsorOptions)
        .then((sponsoredTx) => {
            //console.log(sponsoredTx);
            const { fee, nonce, signer, hashMode } = sponsoredTx.auth.sponsorSpendingCondition;
            const stxAddress = addressToString(addressFromHashMode(hashMode
                , networkObject.chain_id == ChainID.Mainnet ? TransactionVersion.Mainnet : TransactionVersion.Testnet
                , signer));
            return broadcastTransaction(sponsoredTx, networkObject)
                .then(async txResult => {
                    if (txResult.reason === 'ConflictingNonceInMempool') {
                        nextSponsorNonce = nonce + BigInt(1);
                        sponsorStepper = sponsorStepper * BigInt(2);
                    }
                    else {
                        sponsorStepper = BigInt(1);
                        nextSponsorNonce = undefined;
                    }
                    const txid = txResult.txid;
                    console.log(`${stxAddress} ${fee} ${nonce} ${txid}`);
                    return {
                        ...txResult
                        , sponsor_address: stxAddress
                        , fee: +fee.toString()
                    };
                })
                .catch(err => {
                    return Promise.reject(err);
                });
        })
        .catch(err => {
            console.log(`${stxAddress} ${fee} ${nonce}`);
            return Promise.reject(err);
        });
}

export function getContractInfo(contract, type) {
    if (!contract || !contract.address) {
        throw new Error(`contract address not defined: ${contract} ${type}`);
    }
    const x = contract.address.split('.');
    return {
        ...contract,
        principal: x[0],
        contractName: x[1]
    }
}

function escapeRegex(string) {
    return string.replace(/[-\/\\^$*+?.()|[\]{}]/g, '\\$&');
}

function transformContract(data, replaceMap) {
    const x = Object.keys(replaceMap).reduce((s, k) => {
        return data.replace(new RegExp(k, 'g'), replaceMap[k]);
    }, data);
    return x.replace(/\r\n/g, '\n').replace("\ufeff", "");
}

async function sendSignedTransaction(signedTransaction, networkObject, options) {
    return signedTransaction
        .then(async (transaction) => {
            if (transaction.auth.authType == AuthType.Sponsored) {
                let txFee = null;
                const booster = (options || {}).booster;
                switch (transaction.payload.payloadType) {
                    case PayloadType.TokenTransfer:
                        txFee = await estimateTransfer(transaction, networkObject);
                        break;
                    case PayloadType.SmartContract:
                        txFee = await estimateContractDeploy(transaction, networkObject);
                        break;
                    case PayloadType.ContractCall:
                        txFee = await estimateContractFunctionCall(transaction, networkObject);
                        break;
                    default:
                        throw new Error(
                            `Sponsored transactions not supported for transaction type ${PayloadType[transaction.payload.payloadType]
                            }`
                        );
                }
                txFee = txFee * BigInt(booster || 1);
                const serializedTx = transaction.serialize().toString('hex');
                return broadcastSponsoredTransaction(serializedTx, networkObject, txFee);
            } else {
                const { fee, nonce, signer, hashMode } = transaction.auth.spendingCondition;
                const stxAddress = addressToString(addressFromHashMode(hashMode
                    , networkObject.chain_id == ChainID.Mainnet ? TransactionVersion.Mainnet : TransactionVersion.Testnet
                    , signer));
                if (options && options.senderKey && (booster > BigInt(1) || options.booster > 1)) {
                    let txFee = null;
                    switch (transaction.payload.payloadType) {
                        case PayloadType.TokenTransfer:
                            txFee = await estimateTransfer(transaction, networkObject);
                            break;
                        case PayloadType.SmartContract:
                            txFee = await estimateContractDeploy(transaction, networkObject);
                            break;
                        case PayloadType.ContractCall:
                            txFee = await estimateContractFunctionCall(transaction, networkObject);
                            break;
                    }
                    if (txFee) {
                        transaction.setFee(txFee * (options.booster ? BigInt(options.booster) : booster));
                        const privKey = createStacksPrivateKey(options.senderKey);
                        const tx_signer = new TransactionSigner(transaction);
                        tx_signer.signOrigin(privKey);
                    }
                }
                return broadcastTransaction(transaction, networkObject).then(txResult => {
                    const txid = txResult.txid;
                    console.log(`${stxAddress} ${fee} ${nonce} ${txid}`);
                    return txResult;
                });
            }
        })
        .then(txResult => {
            //console.log(txResult);
            if (!txResult.error)
                return txResult;
            else
                return Promise.reject({ message: txResult.reason, data: txResult });
        })
        .catch(err => {
            console.log(err);
            return Promise.reject(err);
        })
}

export async function deployNftTrait(wallet, network, contractName) {
    return new Promise(function (resolve, reject) {

        const replaceMap = {
        }
        readFile('./src/contracts/nft-trait.clar', async function (err, data) {
            if (err) {
                console.log(err);
                reject(err);
            }
            else {
                const clarityCode = transformContract(data.toString(), replaceMap[network] || {});
                const senderKey = wallet._wallet.accounts[0].stxPrivateKey;
                const networkObject = getNetworkObject(network);
                const isSponsored = sponsoredMode;
                const txOptions = {
                    contractName: contractName || 'nft-trait',
                    codeBody: clarityCode,
                    senderKey: senderKey.replace(/^0x/, ''),
                    network: networkObject,
                    sponsored: isSponsored,
                };

                sendSignedTransaction(makeContractDeploy(txOptions), networkObject)
                    .then(txResult => {
                        resolve(txResult);
                    })
                    .catch(err => {
                        reject(err);
                    });
            }
        });
    });
}

export async function deployFtTrait(wallet, network, contractName) {
    return new Promise(function (resolve, reject) {

        const replaceMap = {
        }
        readFile('./src/contracts/sip-010-trait-ft-standard.clar', async function (err, data) {
            if (err) {
                console.log(err);
                reject(err);
            }
            else {
                const clarityCode = transformContract(data.toString(), replaceMap[network] || {});
                const senderKey = wallet._wallet.accounts[0].stxPrivateKey;
                const networkObject = getNetworkObject(network);
                const isSponsored = sponsoredMode;
                const txOptions = {
                    contractName: contractName || 'sip-010-trait-ft-standard',
                    codeBody: clarityCode,
                    senderKey: senderKey.replace(/^0x/, ''),
                    network: networkObject,
                    sponsored: isSponsored,
                };

                sendSignedTransaction(makeContractDeploy(txOptions), networkObject)
                    .then(txResult => {
                        resolve(txResult);
                    })
                    .catch(err => {
                        reject(err);
                    });
            }
        });
    });
}

export async function deployFtContract(wallet, network, contractName) {
    return new Promise(function (resolve, reject) {

        const replaceMap = {
            'mainnet': {
                [escapeRegex('(impl-trait .sip-010-trait-ft-standard.sip-010-trait)')]: '(impl-trait \'SP3FBR2AGK5H9QBDH3EEN6DF8EK8JY7RX8QJ5SVTE.sip-010-trait-ft-standard.sip-010-trait)',
            },
            'testnet': {
                [escapeRegex('(impl-trait .sip-010-trait-ft-standard.sip-010-trait)')]: '(impl-trait \'ST3KG5NBY7ABBT1879Q0MCPK3M7YJZHFWJBF9KHKY.sip-010-trait-ft-standard.sip-010-trait)',
            },
            'regtest': {
                [escapeRegex('(impl-trait .sip-010-trait-ft-standard.sip-010-trait)')]: '(impl-trait \'ST1FA989QSTTKYM4R0H14NGP2TP6FDDKP6CTAWAPG.sip-010-trait-ft-standard.sip-010-trait)',
            }

        }
        readFile('./src/contracts/oas-ft.clar', async function (err, data) {
            if (err) {
                console.log(err);
                reject(err);
            }
            else {
                const clarityCode = transformContract(data.toString(), replaceMap[network] || {});
                const senderKey = wallet._wallet.accounts[0].stxPrivateKey;
                const networkObject = getNetworkObject(network);
                const isSponsored = sponsoredMode;
                const txOptions = {
                    contractName: contractName,
                    codeBody: clarityCode,
                    senderKey: senderKey.replace(/^0x/, ''),
                    network: networkObject,
                    sponsored: isSponsored,
                };

                sendSignedTransaction(makeContractDeploy(txOptions), networkObject)
                    .then(txResult => {
                        resolve(txResult);
                    })
                    .catch(err => {
                        reject(err);
                    });
            }
        });
    });
}

export async function deployNftContract(wallet, network, contractName) {
    return new Promise(function (resolve, reject) {

        const replaceMap = {
            'mainnet': {
                [escapeRegex('(impl-trait .nft-trait.nft-trait)')]: '(impl-trait \'SP2PABAF9FTAJYNFZH93XENAJ8FVY99RRM50D2JG9.nft-trait.nft-trait',
            },
            'testnet': {
                [escapeRegex('(impl-trait .nft-trait.nft-trait)')]: '(impl-trait \'ST2PABAF9FTAJYNFZH93XENAJ8FVY99RRM4DF2YCW.nft-trait.nft-trait)',
            },
            'regtest': {
                [escapeRegex('(impl-trait .nft-trait.nft-trait)')]: '(impl-trait \'ST1FA989QSTTKYM4R0H14NGP2TP6FDDKP6CTAWAPG.nft-trait.nft-trait)',
            }

        }
        readFile('./src/contracts/oas-nft.clar', async function (err, data) {
            if (err) {
                console.log(err);
                reject(err);
            }
            else {
                const clarityCode = transformContract(data.toString(), replaceMap[network] || {});
                const senderKey = wallet._wallet.accounts[0].stxPrivateKey;
                const networkObject = getNetworkObject(network);
                const isSponsored = sponsoredMode;
                const txOptions = {
                    contractName: contractName,
                    codeBody: clarityCode,
                    senderKey: senderKey.replace(/^0x/, ''),
                    network: networkObject,
                    sponsored: isSponsored,
                };

                sendSignedTransaction(makeContractDeploy(txOptions), networkObject)
                    .then(txResult => {
                        resolve(txResult);
                    })
                    .catch(err => {
                        reject(err);
                    });
            }
        });
    });
}

export async function deployMarketContract(wallet, network, contractName) {
    return new Promise(function (resolve, reject) {
        const replaceMap = {}
        readFile('./src/contracts/oas-market.clar', 'utf8', function (err, data) {
            if (err) {
                console.log(err);
                reject(err);
            }
            else {
                const clarityCode = transformContract(data.toString(), replaceMap[network] || {});
                const senderKey = wallet._wallet.accounts[0].stxPrivateKey;
                const networkObject = getNetworkObject(network);
                const isSponsored = sponsoredMode;
                const txOptions = {
                    contractName: contractName,
                    codeBody: clarityCode,
                    senderKey: senderKey.replace(/^0x/, ''),
                    network: networkObject,
                    sponsored: isSponsored,
                };

                sendSignedTransaction(makeContractDeploy(txOptions), networkObject)
                    .then(txResult => {
                        resolve(txResult);
                    })
                    .catch(err => {
                        reject(err);
                    });
            }
        });
    });
}

export async function mintNft(senderKey, tokenUri, network, options) {
    const contract = getContractInfo(getNftContract(network), 'nft');
    const postConditions = [];
    const networkObject = getNetworkObject(network);
    const isSponsored = sponsoredMode;
    const txOptions = {
        contractAddress: contract.principal,
        contractName: contract.contractName,
        functionName: 'claim',
        functionArgs: [stringAsciiCV(tokenUri)],
        validateWithAbi: validateWithAbi,
        postConditionMode: PostConditionMode.Allow,
        postConditions,
        // for backend
        senderKey: senderKey.replace(/^0x/, ''),
        // connect to network go get nonce etc. ?
        network: networkObject,
        anchorMode: AnchorMode.Any,
        sponsored: isSponsored,
        // for browser wallet, useless here
        onFinish: (data) => {
            console.log(data);
            console.log(data.txId);
        }
    };
    // browser plugin
    // openContractCall(txOptions);
    // backend
    return sendSignedTransaction(makeContractCall(txOptions), networkObject, { ...options, senderKey: senderKey.replace(/^0x/, '') });

    return makeContractCall(txOptions)
        .then(transaction => {
            //console.log(transaction);
            if (isSponsored) {
                const serializedTx = transaction.serialize().toString('hex');
                return broadcastSponsoredTransaction(serializedTx, networkObject);
            }
            else {
                return broadcastTransaction(transaction, networkObject);
            }
        })
        .then(txResult => {
            //console.log(txResult);
            if (!txResult.error)
                return txResult;
            else return Promise.reject({ message: txResult.reason, error: txResult.error });
        })
        .catch(err => {
            console.log(err);
            return Promise.reject(err);
        })
}
export async function mintNftFor(senderKey, walletAddress, tokenUri, network, options) {
    const contract = getContractInfo(getNftContract(network), 'nft');
    const postConditions = [];
    const networkObject = getNetworkObject(network);
    const isSponsored = sponsoredMode;

    const txOptions = {
        contractAddress: contract.principal,
        contractName: contract.contractName,
        functionName: 'mint-for',
        functionArgs: [
            principalCV(walletAddress),
            stringAsciiCV(tokenUri)
        ],
        validateWithAbi: validateWithAbi,
        //postConditionMode: PostConditionMode.Allow,
        postConditions,
        // for backend
        senderKey: senderKey.replace(/^0x/, ''),
        sponsored: isSponsored,
        // connect to network go get nonce etc. ?
        network: networkObject,
        anchorMode: AnchorMode.Any,
        // for browser wallet, useless here
        onFinish: (data) => {
            console.log(data);
            console.log(data.txId);
        }
    };
    // browser plugin
    // openContractCall(txOptions);
    // backend
    return sendSignedTransaction(makeContractCall(txOptions), networkObject, options);

    return makeContractCall(txOptions)
        .then(transaction => {
            //console.log(transaction);
            return broadcastTransaction(transaction, networkObject);
        })
        .then(txResult => {
            //console.log(txResult);
            if (!txResult.error)
                return txResult;
            else return Promise.reject({ message: txResult.reason, error: txResult.error });
        })
        .catch(err => {
            console.log(err);
            return Promise.reject(err);
        })
}

export async function getNftPrice(wallet, network, owner, tokenId) {
    const networkObject = getNetworkObject(network);

    const senderAddress = network == "mainnet" ? wallet.stxPubAddressSP : wallet.stxPubAddressST;
    const marketContract = getContractInfo(getMarketContract(network), 'market');
    const nftContract = getContractInfo(getNftContract(network), 'nft');
    const functionName = "get-item";
    const contractAbi = await getContractAbi(marketContract.principal, marketContract.contractName, networkObject);
    const functionAbi = ((contractAbi || {}).functions || []).filter(f => f.name === functionName)[0];
    const funcCallOptions = {
        contractAddress: marketContract.principal,
        contractName: marketContract.contractName,
        functionName: functionName,
        functionArgs: [
            standardPrincipalCV(owner)
            , uintCV(tokenId)
            , contractPrincipalCV(nftContract.principal, nftContract.contractName),
        ],
        senderAddress: senderAddress,
        validateWithAbi: validateWithAbi,
        network: networkObject,
    };
    const result = await callReadOnlyFunction(funcCallOptions);
    return cvToJSON(result);
}

export async function getTokensOwned(wallet, network, owner) {
    const networkObject = getNetworkObject(network);

    const senderAddress = network == "mainnet" ? wallet.stxPubAddressSP : wallet.stxPubAddressST;
    const nftContract = getContractInfo(getNftContract(network), 'nft');
    const functionName = "get-tokens-owned";
    const contractAbi = await getContractAbi(nftContract.principal, nftContract.contractName, networkObject);
    const functionAbi = ((contractAbi || {}).functions || []).filter(f => f.name === functionName)[0];
    const funcCallOptions = {
        contractAddress: nftContract.principal,
        contractName: nftContract.contractName,
        functionName: functionName,
        functionArgs: [
            standardPrincipalCV(owner)
        ],
        senderAddress: senderAddress,
        validateWithAbi: validateWithAbi,
        network: networkObject,
    };
    const result = await callReadOnlyFunction(funcCallOptions);
    return cvToJSON(result);
}

export async function getOwner(wallet, network, tokenId) {
    const networkObject = getNetworkObject(network);

    const senderAddress = network == "mainnet" ? wallet.stxPubAddressSP : wallet.stxPubAddressST;
    const nftContract = getContractInfo(getNftContract(network), 'nft');
    const functionName = "get-owner";
    const contractAbi = await getContractAbi(nftContract.principal, nftContract.contractName, networkObject);
    const functionAbi = ((contractAbi || {}).functions || []).filter(f => f.name === functionName)[0];
    const funcCallOptions = {
        contractAddress: nftContract.principal,
        contractName: nftContract.contractName,
        functionName: functionName,
        functionArgs: [
            uintCV(tokenId)
        ],
        senderAddress: senderAddress,
        validateWithAbi: validateWithAbi,
        network: networkObject,
    };
    const result = await callReadOnlyFunction(funcCallOptions);
    return cvToJSON(result);
}

export async function getTokenUri(wallet, network, tokenId) {
    const networkObject = getNetworkObject(network);

    const senderAddress = network == "mainnet" ? wallet.stxPubAddressSP : wallet.stxPubAddressST;
    const nftContract = getContractInfo(getNftContract(network), 'nft');
    const functionName = "get-token-uri";
    const contractAbi = await getContractAbi(nftContract.principal, nftContract.contractName, networkObject);
    const functionAbi = ((contractAbi || {}).functions || []).filter(f => f.name === functionName)[0];
    const funcCallOptions = {
        contractAddress: nftContract.principal,
        contractName: nftContract.contractName,
        functionName: functionName,
        functionArgs: [
            uintCV(tokenId)
        ],
        senderAddress: senderAddress,
        validateWithAbi: validateWithAbi,
        network: networkObject,
    };
    const result = await callReadOnlyFunction(funcCallOptions);
    return cvToJSON(result);
}

export async function listNft(wallet, network, tokenId, price, options) {
    const senderKey = wallet._wallet.accounts[0].stxPrivateKey;
    const networkObject = getNetworkObject(network);

    const buyerAddress = network == "mainnet" ? wallet.stxPubAddressSP : wallet.stxPubAddressST;
    const nftContract = getContractInfo(getNftContract(network), 'nft');
    const marketContract = getContractInfo(getMarketContract(network), 'market');
    const postConditions = [
    ];
    //const nonce = await getNonce(buyerAddress, networkObject);
    //const fee = new BigNum(1000);
    const isSponsored = sponsoredMode;
    const txOptions = {
        contractAddress: marketContract.principal,
        contractName: marketContract.contractName,
        functionName: 'list-item',
        functionArgs: [
            uintCV(tokenId)
            , uintCV(price)
            , contractPrincipalCV(nftContract.principal, nftContract.contractName)
        ],
        validateWithAbi: validateWithAbi,
        //postConditionMode: PostConditionMode.Allow,
        postConditionMode: PostConditionMode.Deny,
        postConditions,
        // for backend
        senderKey: senderKey.replace(/^0x/, ''),
        sponsored: isSponsored,
        // connect to network go get nonce etc. ?
        network: networkObject,
        anchorMode: AnchorMode.Any,
        //nonce: nonce +  BigInt(1),
        // 
        // fee: fee,
        // for browser plugin
        onFinish: (data) => {
            console.log(data);
            console.log(data.txId);
        }
    };
    // browser plugin
    // openContractCall(txOptions);
    // backend
    return sendSignedTransaction(makeContractCall(txOptions), networkObject, { ...options, senderKey: senderKey.replace(/^0x/, '') });
    return makeContractCall(txOptions)
        .then(async (transaction) => {
            //console.log(transaction);
            const txFee = await estimateContractFunctionCall(transaction, networkObject);
            //transaction.setFee(txFee * BigInt(5));
            return broadcastTransaction(transaction, networkObject);
        })
        .then(txResult => {
            //console.log(txResult);
            if (!txResult.error)
                return txResult;
            else return Promise.reject({ message: txResult.reason, error: txResult.error });
        })
        .catch(err => {
            console.log(err);
            return Promise.reject(err);
        })
}

export async function delistNft(wallet, network, tokenId, price, options) {
    const senderKey = wallet._wallet.accounts[0].stxPrivateKey;
    const networkObject = getNetworkObject(network);

    const buyerAddress = network == "mainnet" ? wallet.stxPubAddressSP : wallet.stxPubAddressST;
    const nftContract = getContractInfo(getNftContract(network), 'nft');
    const marketContract = getContractInfo(getMarketContract(network), 'market');
    const postConditions = [
    ];
    //const nonce = await getNonce(buyerAddress, networkObject);
    //const fee = new BigNum(1000);
    const isSponsored = sponsoredMode;
    const txOptions = {
        contractAddress: marketContract.principal,
        contractName: marketContract.contractName,
        functionName: 'delist-item',
        functionArgs: [
            uintCV(tokenId)
            , contractPrincipalCV(nftContract.principal, nftContract.contractName)
        ],
        validateWithAbi: validateWithAbi,
        //postConditionMode: PostConditionMode.Allow,
        postConditionMode: PostConditionMode.Deny,
        postConditions,
        // for backend
        senderKey: senderKey.replace(/^0x/, ''),
        sponsored: isSponsored,
        // connect to network go get nonce etc. ?
        network: networkObject,
        anchorMode: AnchorMode.Any,
        //nonce: nonce +  BigInt(1),
        // 
        //fee: fee,
        // for browser plugin
        onFinish: (data) => {
            console.log(data);
            console.log(data.txId);
        }
    };
    // browser plugin
    // openContractCall(txOptions);
    // backend
    return sendSignedTransaction(makeContractCall(txOptions), networkObject, options);
    return makeContractCall(txOptions)
        .then(async (transaction) => {
            //console.log(transaction);
            const txFee = await estimateContractFunctionCall(transaction, networkObject);
            //transaction.setFee(txFee * BigInt(5));
            return broadcastTransaction(transaction, networkObject);
        })
        .then(txResult => {
            //console.log(txResult);
            if (!txResult.error)
                return txResult;
            else return Promise.reject({ message: txResult.reason, error: txResult.error });
        })
        .catch(err => {
            console.log(err);
            return Promise.reject(err);
        })
}

export async function purchaseNft(wallet, network, owner, tokenId, price, options) {
    const senderKey = wallet._wallet.accounts[0].stxPrivateKey;
    const networkObject = getNetworkObject(network);
    const feeBooster = (options || {}).booster;
    const buyerAddress = network == "mainnet" ? wallet.stxPubAddressSP : wallet.stxPubAddressST;
    const fromAddress = owner;
    const postConditionAmount = new BigNum(price);
    const nftContract = getContractInfo(getNftContract(network), 'nft');
    const marketContract = getContractInfo(getMarketContract(network), 'market');
    const nonFungibleAssetInfo = createAssetInfo(nftContract.principal, nftContract.contractName, nftContract.assetName);
    const postConditions = [
        // sender limit STX out limit
        makeStandardSTXPostCondition(buyerAddress, FungibleConditionCode.LessEqual, postConditionAmount),
        // nft transferred to buyer so original owner no longer own, this is needed
        makeStandardNonFungiblePostCondition(fromAddress, NonFungibleConditionCode.DoesNotOwn, nonFungibleAssetInfo, uintCV(tokenId)),
        // nft transferred to buyer ??? not sure if this works
        makeStandardNonFungiblePostCondition(buyerAddress, NonFungibleConditionCode.Owns, nonFungibleAssetInfo, uintCV(tokenId)),
    ];
    //const nonce = await getNonce(buyerAddress, networkObject);
    //const fee = feeBooster ? new BigNum(1000);
    const isSponsored = sponsoredMode;
    const txOptions = {
        contractAddress: marketContract.principal,
        contractName: marketContract.contractName,
        functionName: 'purchase-item',
        functionArgs: [
            uintCV(tokenId)
            , contractPrincipalCV(nftContract.principal, nftContract.contractName)],
        validateWithAbi: validateWithAbi,
        //postConditionMode: PostConditionMode.Allow,
        postConditionMode: PostConditionMode.Deny,
        postConditions,
        // for backend
        senderKey: senderKey.replace(/^0x/, ''),
        sponsored: isSponsored,
        // connect to network go get nonce etc. ?
        network: networkObject,
        anchorMode: AnchorMode.Any,
        //nonce: nonce,
        //fee: fee,
        // for browser plugin
        onFinish: (data) => {
            console.log(data);
            console.log(data.txId);
        }
    };
    // browser plugin
    // openContractCall(txOptions);
    // backend
    return sendSignedTransaction(makeContractCall(txOptions), networkObject, options);
    return makeContractCall(txOptions)
        .then(async (transaction) => {
            //console.log(transaction);
            const txFee = await estimateContractFunctionCall(transaction, networkObject);
            //transaction.setFee(txFee * BigInt(5));
            return broadcastTransaction(transaction, networkObject);
        })
        .then(txResult => {
            //console.log(txResult);
            if (!txResult.error)
                return txResult;
            else return Promise.reject({ message: txResult.reason, error: txResult.error });
        })
        .catch(err => {
            console.log(err);
            return Promise.reject(err);
        })
}

export async function purchaseNftDirect(wallet, network, owner, tokenId, price, options) {
    const senderKey = wallet._wallet.accounts[0].stxPrivateKey;
    const networkObject = getNetworkObject(network);

    const buyerAddress = network == "mainnet" ? wallet.stxPubAddressSP : wallet.stxPubAddressST;
    const fromAddress = owner;
    const postConditionAmount = new BigNum(price);
    const nftContract = getContractInfo(getNftContract(network), 'nft');
    const marketContract = getContractInfo(getMarketContract(network), 'market');
    const nonFungibleAssetInfo = createAssetInfo(nftContract.principal, nftContract.contractName, nftContract.assetName);
    const postConditions = [
        // sender limit STX out limit
        makeStandardSTXPostCondition(buyerAddress, FungibleConditionCode.LessEqual, postConditionAmount),
        // nft transferred to buyer so original owner no longer own, this is needed
        makeStandardNonFungiblePostCondition(fromAddress, NonFungibleConditionCode.DoesNotOwn, nonFungibleAssetInfo, uintCV(tokenId)),
        // nft transferred to buyer ??? not sure if this works
        makeStandardNonFungiblePostCondition(buyerAddress, NonFungibleConditionCode.Owns, nonFungibleAssetInfo, uintCV(tokenId)),
    ];
    //const nonce = await getNonce(buyerAddress, networkObject);
    //const fee = new BigNum(1000);
    const isSponsored = sponsoredMode;
    const txOptions = {
        contractAddress: marketContract.principal,
        contractName: marketContract.contractName,
        functionName: 'purchase-item-direct',
        functionArgs: [
            uintCV(tokenId)
            , contractPrincipalCV(nftContract.principal, nftContract.contractName)],
        validateWithAbi: validateWithAbi,
        //postConditionMode: PostConditionMode.Allow,
        postConditionMode: PostConditionMode.Deny,
        postConditions,
        // for backend
        senderKey: senderKey.replace(/^0x/, ''),
        sponsored: isSponsored,
        // connect to network go get nonce etc. ?
        network: networkObject,
        anchorMode: AnchorMode.Any,
        //nonce: nonce +  BigInt(1),
        //fee: fee,
        // for browser plugin
        onFinish: (data) => {
            console.log(data);
            console.log(data.txId);
        }
    };
    // browser plugin
    // openContractCall(txOptions);
    // backend
    return sendSignedTransaction(makeContractCall(txOptions), networkObject, options);
    return makeContractCall(txOptions)
        .then(async (transaction) => {
            //console.log(transaction);
            const txFee = await estimateContractFunctionCall(transaction, networkObject);
            //transaction.setFee(txFee * BigInt(5));
            return broadcastTransaction(transaction, networkObject);
        })
        .then(txResult => {
            //console.log(txResult);
            if (!txResult.error)
                return txResult;
            else return Promise.reject({ message: txResult.reason, error: txResult.error });
        })
        .catch(err => {
            console.log(err);
            return Promise.reject(err);
        })
}

export async function confirmPurchaseNft(wallet, network, owner, tokenId, price, options) {
    const senderKey = wallet._wallet.accounts[0].stxPrivateKey;
    const networkObject = getNetworkObject(network);

    const buyerAddress = network == "mainnet" ? wallet.stxPubAddressSP : wallet.stxPubAddressST;
    const fromAddress = owner;
    const postConditionAmount = new BigNum(price);
    const nftContract = getContractInfo(getNftContract(network), 'nft');
    const marketContract = getContractInfo(getMarketContract(network), 'market');
    const nonFungibleAssetInfo = createAssetInfo(nftContract.principal, nftContract.contractName, nftContract.assetName);
    const postConditions = [
        // sender limit STX out limit(the market contract)
        makeContractSTXPostCondition(
            marketContract.principal, marketContract.contractName
            , FungibleConditionCode.LessEqual, postConditionAmount),
        // nft transferred to buyer so original owner no longer own, this is needed
        makeContractNonFungiblePostCondition(
            marketContract.principal, marketContract.contractName
            , NonFungibleConditionCode.DoesNotOwn, nonFungibleAssetInfo, uintCV(tokenId)),
        // nft transferred to buyer ??? makes no diff as there is no transfer from !!!!
        makeStandardNonFungiblePostCondition(buyerAddress, NonFungibleConditionCode.Owns, nonFungibleAssetInfo, uintCV(tokenId)),
    ];
    //const nonce = await getNonce(buyerAddress, networkObject);
    //const fee = new BigNum(1000);
    const isSponsored = sponsoredMode;
    const txOptions = {
        contractAddress: marketContract.principal,
        contractName: marketContract.contractName,
        functionName: 'confirm-item',
        functionArgs: [
            uintCV(tokenId)
            , contractPrincipalCV(nftContract.principal, nftContract.contractName)],
        validateWithAbi: validateWithAbi,
        //postConditionMode: PostConditionMode.Allow,
        postConditionMode: PostConditionMode.Deny,
        postConditions,
        // for backend
        senderKey: senderKey.replace(/^0x/, ''),
        sponsored: isSponsored,
        // connect to network go get nonce etc. ?
        network: networkObject,
        anchorMode: AnchorMode.Any,
        //nonce: nonce + BigInt(1),
        //fee: fee,
        // for browser plugin
        onFinish: (data) => {
            console.log(data);
            console.log(data.txId);
        }
    };
    // browser plugin
    // openContractCall(txOptions);
    // backend
    return sendSignedTransaction(makeContractCall(txOptions), networkObject, options);
    return makeContractCall(txOptions)
        .then(async (transaction) => {
            //console.log(transaction);
            const txFee = await estimateContractFunctionCall(transaction, networkObject);
            //transaction.setFee(txFee * BigInt(2));
            return broadcastTransaction(transaction, networkObject);
        })
        .then(txResult => {
            //console.log(txResult);
            if (!txResult.error)
                return txResult;
            else return Promise.reject({ message: txResult.reason, error: txResult.error });
        })
        .catch(err => {
            console.log(err);
            return Promise.reject(err);
        })
}

export async function transferNft(wallet, network, toAddress, tokenId) {
    // Add an optional post condition
    // See below for details on constructing post 
    const senderKey = wallet._wallet.accounts[0].stxPrivateKey;
    const networkObject = getNetworkObject(network);

    const fromAddress = network == "mainnet" ? wallet.stxPubAddressSP : wallet.stxPubAddressST;
    const nftContract = getContractInfo(getNftContract(network), 'nft');
    const postConditionAddress = fromAddress;
    const postConditionCode = NonFungibleConditionCode.DoesNotOwn;
    const assetAddress = nftContract.principal;
    const assetContractName = nftContract.contractName;
    const assetName = nftContract.assetName; // defined in 
    const tokenAssetName = tokenId;
    const nonFungibleAssetInfo = createAssetInfo(assetAddress, assetContractName, assetName);
    const postConditions = [
        makeStandardNonFungiblePostCondition(postConditionAddress, postConditionCode, nonFungibleAssetInfo, uintCV(tokenId)),
    ];
    const isSponsored = sponsoredMode;

    const txOptions = {
        contractAddress: nftContract.principal,
        contractName: nftContract.contractName,
        functionName: 'transfer',
        functionArgs: [uintCV(tokenId), standardPrincipalCV(fromAddress), standardPrincipalCV(toAddress)],
        validateWithAbi: validateWithAbi,
        postConditionMode: PostConditionMode.Deny,
        postConditions,
        // for backend
        senderKey: senderKey,
        sponsored: isSponsored,
        // connect to network go get nonce etc. ?
        network: networkObject,
        anchorMode: AnchorMode.Any,
        // for browser plugin
        onFinish: (data) => {
            console.log(data);
            console.log(data.txId);
        }
    };
    // browser plugin
    // openContractCall(txOptions);
    // backend
    return sendSignedTransaction(makeContractCall(txOptions), networkObject);
    return makeContractCall(txOptions)
        .then(transaction => {
            //console.log(transaction);
            return broadcastTransaction(transaction, networkObject);
        })
        .then(txResult => {
            // console.log(txResult);
            if (!txResult.error)
                return txResult;
            else return Promise.reject({ message: txResult.reason, error: txResult.error });
        })
        .catch(err => {
            console.log(err);
            return Promise.reject(err);
        })
}

export async function transferFt(wallet, network, fromAddress, toAddress, amount) {
    // Add an optional post condition
    // See below for details on constructing post 
    const senderKey = wallet._wallet.accounts[0].stxPrivateKey;
    const networkObject = getNetworkObject(network);

    //const fromAddress = network == "mainnet" ? wallet.stxPubAddressSP : wallet.stxPubAddressST;
    const ftContract = getContractInfo(getFtContract(network), 'ft');
    const postConditionAddress = fromAddress;
    const postConditionCode = FungibleConditionCode.Equal;
    const assetAddress = ftContract.principal;
    const assetContractName = ftContract.contractName;
    const assetName = ftContract.assetName; // defined in 
    const fungibleAssetInfo = createAssetInfo(assetAddress, assetContractName, assetName);
    const postConditions = [
        makeStandardFungiblePostCondition(postConditionAddress, postConditionCode, new BigNum(amount), fungibleAssetInfo),
    ];
    const isSponsored = sponsoredMode;

    const txOptions = {
        contractAddress: ftContract.principal,
        contractName: ftContract.contractName,
        functionName: 'transfer',
        functionArgs: [uintCV(amount), standardPrincipalCV(fromAddress), standardPrincipalCV(toAddress), noneCV()],
        validateWithAbi: validateWithAbi,
        postConditionMode: PostConditionMode.Deny,
        postConditions,
        // for backend
        senderKey: senderKey,
        sponsored: isSponsored,
        // connect to network go get nonce etc. ?
        network: networkObject,
        anchorMode: AnchorMode.Any,
        // for browser plugin
        onFinish: (data) => {
            console.log(data);
            console.log(data.txId);
        }
    };
    // browser plugin
    // openContractCall(txOptions);
    // backend
    return sendSignedTransaction(makeContractCall(txOptions), networkObject);
}

export async function getFtXRate(wallet, network, amount) {
    const networkObject = getNetworkObject(network);

    const senderAddress = network == "mainnet" ? wallet.stxPubAddressSP : wallet.stxPubAddressST;
    const ftContract = getContractInfo(getFtContract(network), 'ft');
    const functionName = "get-quote";
    const contractAbi = await getContractAbi(ftContract.principal, ftContract.contractName, networkObject);
    const functionAbi = ((contractAbi || {}).functions || []).filter(f => f.name === functionName)[0];
    const funcCallOptions = {
        contractAddress: ftContract.principal,
        contractName: ftContract.contractName,
        functionName: functionName,
        functionArgs: [
            uintCV(amount)
        ],
        senderAddress: senderAddress,
        validateWithAbi: validateWithAbi,
        network: networkObject,
    };
    const result = await callReadOnlyFunction(funcCallOptions);
    return cvToJSON(result);
}

export async function mintFt(wallet, network, amount) {
    // Add an optional post condition
    // See below for details on constructing post 
    const senderKey = wallet._wallet.accounts[0].stxPrivateKey;
    const networkObject = getNetworkObject(network);
    const xRate = await getFtXRate(wallet, network, amount);
    const stx = +xRate.value.stx.value;
    const token = +xRate.value.token.value;
    const remain = +xRate.value.remain.value;
    const floorStxPostConditionAmount = new BigNum(stx >= 100 ? +stx - 100 : 0);
    const ceilingStxPostConditionAmount = new BigNum(stx > 0 ? +stx + 100 : 0);
    const floorTokenPostConditionAmount = new BigNum(+token - 100);
    const ceilingTokenPostConditionAmount = new BigNum(+token + 100);

    const fromAddress = network == "mainnet" ? wallet.stxPubAddressSP : wallet.stxPubAddressST;
    const ftContract = getContractInfo(getFtContract(network), 'ft');
    const postConditionAddress = fromAddress;
    const postConditionCode = FungibleConditionCode.LessEqual;
    const assetAddress = ftContract.principal;
    const assetContractName = ftContract.contractName;
    const assetName = ftContract.assetName; // defined in 
    const fungibleAssetInfo = createAssetInfo(assetAddress, assetContractName, assetName);
    const postConditions = [
        makeStandardSTXPostCondition(fromAddress, FungibleConditionCode.LessEqual, ceilingStxPostConditionAmount),
        makeStandardSTXPostCondition(fromAddress, FungibleConditionCode.GreaterEqual, floorStxPostConditionAmount),
    ];
    const isSponsored = sponsoredMode;

    const txOptions = {
        contractAddress: ftContract.principal,
        contractName: ftContract.contractName,
        functionName: 'mint',
        functionArgs: [uintCV(amount)],
        validateWithAbi: validateWithAbi,
        postConditionMode: PostConditionMode.Deny,
        postConditions,
        // for backend
        senderKey: senderKey,
        sponsored: isSponsored,
        // connect to network go get nonce etc. ?
        network: networkObject,
        anchorMode: AnchorMode.Any,
        // for browser plugin
        onFinish: (data) => {
            console.log(data);
            console.log(data.txId);
        }
    };
    // browser plugin
    // openContractCall(txOptions);
    // backend
    return sendSignedTransaction(makeContractCall(txOptions), networkObject);
}

export async function redeemFt(wallet, network, amount) {
    // Add an optional post condition
    // See below for details on constructing post 
    const senderKey = wallet._wallet.accounts[0].stxPrivateKey;
    const networkObject = getNetworkObject(network);
    const xRate = await getFtXRate(wallet, network, amount);
    const stx = +xRate.value.stx.value;
    const token = +xRate.value.token.value;
    const remain = +xRate.value.remain.value;
    const floorStxPostConditionAmount = new BigNum(stx >= 100 ? +stx - 100 : 0);
    const ceilingStxPostConditionAmount = new BigNum(stx > 0 ? +stx + 100 : 0);
    const floorTokenPostConditionAmount = new BigNum(+token - 100);
    const ceilingTokenPostConditionAmount = new BigNum(+token + 100);

    const fromAddress = network == "mainnet" ? wallet.stxPubAddressSP : wallet.stxPubAddressST;
    const ftContract = getContractInfo(getFtContract(network), 'ft');
    const postConditionAddress = fromAddress;
    const postConditionCode = FungibleConditionCode.LessEqual;
    const assetAddress = ftContract.principal;
    const assetContractName = ftContract.contractName;
    const assetName = ftContract.assetName; // defined in 
    const fungibleAssetInfo = createAssetInfo(assetAddress, assetContractName, assetName);
    const postConditions = [
        makeStandardFungiblePostCondition(fromAddress, FungibleConditionCode.LessEqual, ceilingTokenPostConditionAmount, fungibleAssetInfo),
        makeStandardFungiblePostCondition(fromAddress, FungibleConditionCode.GreaterEqual, floorTokenPostConditionAmount, fungibleAssetInfo),
        makeContractSTXPostCondition(assetAddress, assetContractName, FungibleConditionCode.LessEqual, ceilingStxPostConditionAmount),
        makeContractSTXPostCondition(assetAddress, assetContractName, FungibleConditionCode.GreaterEqual, floorStxPostConditionAmount),
    ];
    const isSponsored = sponsoredMode;

    const txOptions = {
        contractAddress: ftContract.principal,
        contractName: ftContract.contractName,
        functionName: 'redeem',
        functionArgs: [uintCV(amount)],
        validateWithAbi: validateWithAbi,
        postConditionMode: PostConditionMode.Deny,
        postConditions,
        // for backend
        senderKey: senderKey,
        sponsored: isSponsored,
        // connect to network go get nonce etc. ?
        network: networkObject,
        anchorMode: AnchorMode.Any,
        // for browser plugin
        onFinish: (data) => {
            console.log(data);
            console.log(data.txId);
        }
    };
    // browser plugin
    // openContractCall(txOptions);
    // backend
    return sendSignedTransaction(makeContractCall(txOptions), networkObject);
}

export async function approveFtTransfer(wallet, network, spender, amount) {
    // Add an optional post condition
    // See below for details on constructing post 
    const senderKey = wallet._wallet.accounts[0].stxPrivateKey;
    const networkObject = getNetworkObject(network);

    const fromAddress = network == "mainnet" ? wallet.stxPubAddressSP : wallet.stxPubAddressST;
    const ftContract = getContractInfo(getFtContract(network), 'ft');
    const assetAddress = ftContract.principal;
    const assetContractName = ftContract.contractName;
    const assetName = ftContract.assetName; // defined in 
    const postConditions = [
    ];
    const isSponsored = sponsoredMode;

    const txOptions = {
        contractAddress: ftContract.principal,
        contractName: ftContract.contractName,
        functionName: 'approve',
        functionArgs: [principalCV(fromAddress), uintCV(amount)],
        validateWithAbi: validateWithAbi,
        postConditionMode: PostConditionMode.Deny,
        postConditions,
        // for backend
        senderKey: senderKey,
        sponsored: isSponsored,
        // connect to network go get nonce etc. ?
        network: networkObject,
        anchorMode: AnchorMode.Any,
        // for browser plugin
        onFinish: (data) => {
            console.log(data);
            console.log(data.txId);
        }
    };
    // browser plugin
    // openContractCall(txOptions);
    // backend
    return sendSignedTransaction(makeContractCall(txOptions), networkObject);
}

export async function withdrawFtRemainingStx(wallet, network) {
    // Add an optional post condition
    // See below for details on constructing post 
    const senderKey = wallet._wallet.accounts[0].stxPrivateKey;
    const networkObject = getNetworkObject(network);

    const fromAddress = network == "mainnet" ? wallet.stxPubAddressSP : wallet.stxPubAddressST;
    const ftContract = getContractInfo(getFtContract(network), 'ft');
    const assetAddress = ftContract.principal;
    const assetContractName = ftContract.contractName;
    const assetName = ftContract.assetName; // defined in 
    const postConditions = [
        makeContractSTXPostCondition(assetAddress, assetContractName, FungibleConditionCode.GreaterEqual, 0),
    ];
    const isSponsored = sponsoredMode;

    const txOptions = {
        contractAddress: ftContract.principal,
        contractName: ftContract.contractName,
        functionName: 'withdraw-remain',
        functionArgs: [],
        validateWithAbi: validateWithAbi,
        postConditionMode: PostConditionMode.Deny,
        postConditions,
        // for backend
        senderKey: senderKey,
        sponsored: isSponsored,
        // connect to network go get nonce etc. ?
        network: networkObject,
        anchorMode: AnchorMode.Any,
        // for browser plugin
        onFinish: (data) => {
            console.log(data);
            console.log(data.txId);
        }
    };
    // browser plugin
    // openContractCall(txOptions);
    // backend
    return sendSignedTransaction(makeContractCall(txOptions), networkObject);
}
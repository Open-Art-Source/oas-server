// due to the 'load' nature of dotenv, process.env may not be available in
// other package/modules if ued directly
// we wrap them here so it is 'deferred'(i.e. only retrieve via fn calls)

require('dotenv').config();
import { TransactionVersion } from '@stacks/transactions';
import { StacksTestnet, StacksMainnet } from '@stacks/network';

export function getEnv(key) {
    return process.env[key];
}

export function getStacksApiEndpoint(network, version = 1) {
    const vpath = version === 1
        ? "/extended/v1"
        : version === 2 ? "/v2"
            : "";

    const api_endpoint = network == "mainnet"
        ? (getEnv('MAINNET_API_ENDPOINT') || 'https://stacks-node-api.mainnet.stacks.co') + vpath
        : network == 'regtest' ? (getEnv('REGTEST_API_ENDPOINT') || 'https://stacks-node-api.regtest.stacks.co') + vpath
            : (getEnv('TESTNET_API_ENDPOINT') || 'https://stacks-node-api.testnet.stacks.co') + vpath;

    return api_endpoint;
}

export function getNetworkObject(network) {
    return network == "mainnet"
        ? new StacksMainnet()
        : network == "testnet" ? new StacksTestnet()
            : new StacksTestnet({ url: getStacksApiEndpoint(network, 0) });
}

export function getNftContract(network) {

    if (network == "mainnet") {
        const nftContractAddress = getEnv('MAINNET_NFT_CONTRACT') || 'SP3KG5NBY7ABBT1879Q0MCPK3M7YJZHFWJBAEDJ93.Artie';
        const nftTokenName = getEnv('MAINNET_NFT_TOKEN') || 'OpenArtSource';
        return {
            address: nftContractAddress,
            assetName: nftTokenName,
            transactionVersion: TransactionVersion.Mainnet
        }
    } else if (network == "testnet") {
        const nftContractAddress = getEnv('TESTNET_NFT_CONTRACT') || 'ST3KG5NBY7ABBT1879Q0MCPK3M7YJZHFWJBF9KHKY.Artie';
        const nftTokenName = getEnv('TESTNET_NFT_TOKEN') || 'OpenArtSource';
        return {
            address: nftContractAddress,
            assetName: nftTokenName,
            transactionVersion: TransactionVersion.Testnet
        }
    } else {
        const nftContractAddress = getEnv('REGTEST_NFT_CONTRACT') || 'ST1FA989QSTTKYM4R0H14NGP2TP6FDDKP6CTAWAPG.Artie';
        const nftTokenName = getEnv('REGTEST_NFT_TOKEN') || 'OpenArtSource';
        return {
            address: nftContractAddress,
            assetName: nftTokenName,
            transactionVersion: TransactionVersion.Testnet
        }

    }
}

export function getFtContract(network) {

    if (network == "mainnet") {
        const ftContractAddress = getEnv('MAINNET_FT_CONTRACT');
        const ftTokenName = getEnv('MAINNET_FT_TOKEN') || 'oas-token';
        return {
            address: ftContractAddress,
            assetName: ftTokenName,
            transactionVersion: TransactionVersion.Mainnet
        }
    } else if (network == "testnet") {
        const ftContractAddress = getEnv('TESTNET_FT_CONTRACT') || 'ST3KG5NBY7ABBT1879Q0MCPK3M7YJZHFWJBF9KHKY.ft7';
        const ftTokenName = getEnv('TESTNET_FT_TOKEN') || 'oas-token';
        return {
            address: ftContractAddress,
            assetName: ftTokenName,
            transactionVersion: TransactionVersion.Testnet
        }
    } else {
        const ftContractAddress = getEnv('REGTEST_FT_CONTRACT');
        const ftTokenName = getEnv('REGTEST_FT_TOKEN') || 'oas-token';
        return {
            address: ftContractAddress,
            assetName: ftTokenName,
            transactionVersion: TransactionVersion.Testnet
        }

    }
}


export function getMarketContract(network) {
    if (network == "mainnet") {
        const marketContractAddress = getEnv('MAINNET_MARKET_CONTRACT');
        return {
            address: marketContractAddress,
            //assetName: 'OpenArtSource',
            transactionVersion: TransactionVersion.Mainnet
        }
    } else if (network == "testnet") {
        const marketContractAddress = getEnv('TESTNET_MARKET_CONTRACT') || 'ST3KG5NBY7ABBT1879Q0MCPK3M7YJZHFWJBF9KHKY.market9';
        return {
            address: marketContractAddress,
            //assetName: 'OpenArtSource',
            transactionVersion: TransactionVersion.Testnet
        }
    } else {
        const marketContractAddress = getEnv('REGTEST_MARKET_CONTRACT') || 'ST1FA989QSTTKYM4R0H14NGP2TP6FDDKP6CTAWAPG.market1';
        return {
            address: marketContractAddress,
            //assetName: 'OpenArtSource',
            transactionVersion: TransactionVersion.Testnet
        }
    }
}

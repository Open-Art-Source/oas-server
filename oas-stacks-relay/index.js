//const express = require("express");
//const bodyParser = require("body-parser");
//const { JSONRPCServer } = require("json-rpc-2.0");

import express from "express";
import { JSONRPCServer, createJSONRPCErrorResponse } from "json-rpc-2.0";
import { createWallet, encryptMnemonic, decryptMnemonic, nodeWallet, loadWallet } from "./src/wallet";
import {
  transferNft, mintNft, mintNftFor, listNft, delistNft
  , purchaseNft, purchaseNftDirect, getNftPrice, confirmPurchaseNft, getTokensOwned, getOwner, getTokenUri
  , deployNftContract, deployMarketContract, deployNftTrait, deployFtContract, deployFtTrait
  , transferFt, mintFt, redeemFt, approveFtTransfer, withdrawFtRemainingStx
} from "./src/transactions";
import { Buffer } from 'buffer';
import axios from "axios";
import { getEnv, getStacksApiEndpoint } from './src/config';
//var axios = require("axios").default;

const server = new JSONRPCServer();
const default_network = getEnv('NETWORK') || "regtest";

loadWallet()
  .then(() => {
    console.log(`default network ${default_network} `)
  })
  .catch(err => {
    console.log(err)
  });

// First parameter is a method name.
// Second parameter is a method itself.
// A method takes JSON-RPC params and returns a result.
// It can also return a promise of the result.
server.addMethod("create_wallet", async ([password], serverParams) => {
  const wallet = await createWallet(undefined, password);
  const encryptedMnemonic = wallet.mnemonic;
  return { secret: encryptedMnemonic, testnetAddress: wallet.stxPubAddressST, mainnetAddress: wallet.stxPubAddressSP };
});
server.addMethod("mint_nft_token", async ([tokenUri, encryptedMnemonic, password, options], serverParams) => {
  const b = Buffer.from(encryptedMnemonic.replace(/^0x/, ''), "hex")
  const mnemonic = await decryptMnemonic(b, password);
  const wallet = await createWallet(mnemonic, password);
  const txResult = await mintNft(wallet._wallet.accounts[0].stxPrivateKey, tokenUri, default_network, options);
  return txResult;
});

server.addMethod("mint_nft_token_for", async ([tokenUri, walletAddress, encryptedMnemonic, password, options], serverParams) => {
  const network = walletAddress.match(/^SP/) ? "mainnet" : "testnet";
  const b = Buffer.from(encryptedMnemonic.replace(/^0x/, ''), "hex")
  const mnemonic = await decryptMnemonic(b, password);
  const wallet = await createWallet(mnemonic, password);
  const txResult = await mintNftFor(wallet._wallet.accounts[0].stxPrivateKey, walletAddress, tokenUri, network, options);
  return txResult;
});

server.addMethod("list_nft_token", async ([owner, tokenId, price, encryptedMnemonic, password, options], serverParams) => {
  const network = owner.match(/^SP/) ? "mainnet" : "testnet";
  const b = Buffer.from(encryptedMnemonic.replace(/^0x/, ''), "hex")
  const mnemonic = await decryptMnemonic(b, password);
  const wallet = await createWallet(mnemonic, password);
  const txResult = await listNft(wallet, network, tokenId, price, options);
  return txResult;
});

server.addMethod("delist_nft_token", async ([owner, tokenId, encryptedMnemonic, password, options], serverParams) => {
  const network = owner.match(/^SP/) ? "mainnet" : "testnet";
  const b = Buffer.from(encryptedMnemonic.replace(/^0x/, ''), "hex")
  const mnemonic = await decryptMnemonic(b, password);
  const wallet = await createWallet(mnemonic, password);
  const txResult = await delistNft(wallet, network, tokenId, options);
  return txResult;
});

server.addMethod("deploy_nft_trait", async ([contractName, network, encryptedMnemonic, password], serverParams) => {
  const b = Buffer.from(encryptedMnemonic.replace(/^0x/, ''), "hex")
  const mnemonic = await decryptMnemonic(b, password);
  const wallet = await createWallet(mnemonic, password);
  const txResult = await deployNftTrait(wallet, network, contractName);
  return txResult;
});

server.addMethod("deploy_ft_trait", async ([contractName, network, encryptedMnemonic, password], serverParams) => {
  const b = Buffer.from(encryptedMnemonic.replace(/^0x/, ''), "hex")
  const mnemonic = await decryptMnemonic(b, password);
  const wallet = await createWallet(mnemonic, password);
  const txResult = await deployFtTrait(wallet, network, contractName);
  return txResult;
});

server.addMethod("deploy_nft_contract", async ([contractName, network, encryptedMnemonic, password], serverParams) => {
  const b = Buffer.from(encryptedMnemonic.replace(/^0x/, ''), "hex")
  const mnemonic = await decryptMnemonic(b, password);
  const wallet = await createWallet(mnemonic, password);
  const txResult = await deployNftContract(wallet, network, contractName);
  return txResult;
});

server.addMethod("deploy_ft_contract", async ([contractName, network, encryptedMnemonic, password], serverParams) => {
  const b = Buffer.from(encryptedMnemonic.replace(/^0x/, ''), "hex")
  const mnemonic = await decryptMnemonic(b, password);
  const wallet = await createWallet(mnemonic, password);
  const txResult = await deployFtContract(wallet, network, contractName);
  return txResult;
});

server.addMethod("deploy_market_contract", async ([contractName, network, encryptedMnemonic, password], serverParams) => {
  const b = Buffer.from(encryptedMnemonic.replace(/^0x/, ''), "hex")
  const mnemonic = await decryptMnemonic(b, password);
  const wallet = await createWallet(mnemonic, password);
  const txResult = await deployMarketContract(wallet, network, contractName);
  return txResult;
});

server.addMethod("purchase_nft_token", async ([owner, tokenId, price, encryptedMnemonic, password, options], serverParams) => {
  const network = owner.match(/^SP/) ? "mainnet" : "testnet";
  const b = Buffer.from(encryptedMnemonic.replace(/^0x/, ''), "hex")
  const mnemonic = await decryptMnemonic(b, password);
  const wallet = await createWallet(mnemonic, password);
  const txResult = await purchaseNft(wallet, network, owner, tokenId, price, options);
  return txResult;
});

server.addMethod("purchase_nft_token_direct", async ([owner, tokenId, price, encryptedMnemonic, password, options], serverParams) => {
  const network = owner.match(/^SP/) ? "mainnet" : "testnet";
  const b = Buffer.from(encryptedMnemonic.replace(/^0x/, ''), "hex")
  const mnemonic = await decryptMnemonic(b, password);
  const wallet = await createWallet(mnemonic, password);
  const txResult = await purchaseNftDirect(wallet, network, owner, tokenId, price, options);
  return txResult;
});

server.addMethod("transfer_nft_token", async ([owner, to, tokenId, encryptedMnemonic, password, options], serverParams) => {
  const network = owner.match(/^SP/) ? "mainnet" : "testnet";
  const b = Buffer.from(encryptedMnemonic.replace(/^0x/, ''), "hex")
  const mnemonic = await decryptMnemonic(b, password);
  const wallet = await createWallet(mnemonic, password);
  //console.log(wallet.stxPubAddressSP);
  //console.log(wallet.stxPubAddressST);
  const txResult = await transferNft(wallet, network, to, tokenId, options);
  return txResult;
});

server.addMethod("confirm_nft_token", async ([owner, tokenId, price, encryptedMnemonic, password, options], serverParams) => {
  const network = owner.match(/^SP/) ? "mainnet" : "testnet";
  const b = Buffer.from(encryptedMnemonic.replace(/^0x/, ''), "hex")
  const mnemonic = await decryptMnemonic(b, password);
  const wallet = await createWallet(mnemonic, password);
  const txResult = await confirmPurchaseNft(wallet, network, owner, tokenId, price);
  return txResult;
});

server.addMethod("mint_ft_token", async ([amount, encryptedMnemonic, password, options], serverParams) => {
  const b = Buffer.from(encryptedMnemonic.replace(/^0x/, ''), "hex")
  const mnemonic = await decryptMnemonic(b, password);
  const wallet = await createWallet(mnemonic, password);
  const txResult = await mintFt(wallet, default_network, amount);
  return txResult;
});

server.addMethod("transfer_ft_token", async ([fromAddress, toAddress, amount, encryptedMnemonic, password], serverParams) => {
  const network = toAddress.match(/^SP/) ? "mainnet" : "testnet";
  const b = Buffer.from(encryptedMnemonic.replace(/^0x/, ''), "hex")
  const mnemonic = await decryptMnemonic(b, password);
  const wallet = await createWallet(mnemonic, password);
  const txResult = await transferFt(wallet, network, fromAddress, toAddress, amount);
  return txResult;
});

server.addMethod("redeem_ft_token", async ([amount, encryptedMnemonic, password], serverParams) => {
  const b = Buffer.from(encryptedMnemonic.replace(/^0x/, ''), "hex")
  const mnemonic = await decryptMnemonic(b, password);
  const wallet = await createWallet(mnemonic, password);
  const txResult = await redeemFt(wallet, default_network, amount);
  return txResult;
});

server.addMethod("approve_ft_token_spender", async ([spenderAddress, amount, encryptedMnemonic, password], serverParams) => {
  const network = spenderAddress.match(/^SP/) ? "mainnet" : "testnet";
  const b = Buffer.from(encryptedMnemonic.replace(/^0x/, ''), "hex")
  const mnemonic = await decryptMnemonic(b, password);
  const wallet = await createWallet(mnemonic, password);
  const txResult = await approveFtTransfer(wallet, network, spenderAddress, amount);
  return txResult;
});

server.addMethod("withdraw_ft_token_stx", async ([encryptedMnemonic, password], serverParams) => {
  const network = default_network;
  const b = Buffer.from(encryptedMnemonic.replace(/^0x/, ''), "hex")
  const mnemonic = await decryptMnemonic(b, password);
  const wallet = await createWallet(mnemonic, password);
  const txResult = await withdrawFtRemainingStx(wallet, network);
  return txResult;
});

server.addMethod("get_nft_token_price", async ([owner, tokenId], serverParams) => {
  const network = owner.match(/^SP/) ? "mainnet" : "testnet";
  const result = await getNftPrice(nodeWallet, network, owner, tokenId);
  return result;
});

server.addMethod("get_tokens_owned", async ([owner], serverParams) => {
  const network = owner.match(/^SP/) ? "mainnet" : "testnet";
  const result = await getTokensOwned(nodeWallet, network, owner);
  return result;
});

server.addMethod("get_owner", async ([tokenId, network = default_network], serverParams) => {
  const result = await getOwner(nodeWallet, network, tokenId);
  return result;
});

server.addMethod("get_token_uri", async ([tokenId, network = default_network], serverParams) => {
  const result = await getTokenUri(nodeWallet, network, tokenId);
  return result;
});

server.addMethod("get_transaction", async ([txid, network = default_network], serverParams) => {
  const api_endpoint = getStacksApiEndpoint(network, 1);

  return axios({
    method: 'GET',
    url: api_endpoint + '/tx/' + txid + "?unanchored=true",
    headers: {
    },
    /* data to be sent, must be json */
    // data: {
    //   jobId: 1
    // }
  }).then(result => {
    if (result.data) {
      const txInfo = result.data;
      const tx_status = txInfo.tx_status;
      const runtime_cost = txInfo.execution_cost_read_count
        + txInfo.execution_cost_read_length
        + txInfo.execution_cost_runtime
        + txInfo.execution_cost_write_count
        + txInfo.execution_cost_write_length;
      const fee_rate = txInfo.fee_rate;
      const fee = fee_rate;
      const tx_result = {
        sender_address: txInfo.sender_address,
        sponsor_address: txInfo.sponsor_address,
        fee_rate: txInfo.fee_rate,
        fee: fee,
        nonce: txInfo.nonce,
        sponsored: txInfo.sponsored,
        runtime_cost: runtime_cost,
        receipt_time: txInfo.receipt_time,
        receipt_time_iso: txInfo.receipt_time_iso,
        tx_id: txInfo.tx_id,
        tx_status: txInfo.tx_status,
        tx_result: txInfo.tx_result,
        events: txInfo.events,
      };

      if (tx_status !== 'pending')
        return tx_result;
      else
        return axios({
          method: 'GET',
          url: api_endpoint + '/microblock/unanchored/txs',
          headers: {
          },
          /* data to be sent, must be json */
          // data: {
          //   jobId: 1
          // }
        }).then(result => {
          const tx_micro_block = (result.data.results || []).filter(t => {
            return t.tx_id === ('0x' + txid).replace(/^0x0x/i,'0x');
          }).map(txInfo => {
            const runtime_cost = txInfo.execution_cost_read_count
              + txInfo.execution_cost_read_length
              + txInfo.execution_cost_runtime
              + txInfo.execution_cost_write_count
              + txInfo.execution_cost_write_length;
            const fee_rate = txInfo.fee_rate;
            const fee = fee_rate;
            return {
              sender_address: txInfo.sender_address,
              sponsor_address: txInfo.sponsor_address,
              fee_rate: txInfo.fee_rate,
              fee: fee,
              nonce: txInfo.nonce,
              sponsored: txInfo.sponsored,
              runtime_cost: runtime_cost,
              receipt_time: txInfo.receipt_time,
              receipt_time_iso: txInfo.receipt_time_iso,
              tx_id: txInfo.tx_id,
              tx_status: txInfo.tx_status,
              tx_result: txInfo.tx_result,
              events: txInfo.events,
              microblock: true,
            };
          })[0];
          return tx_micro_block || tx_result;
        }).catch(error=>{
          return Promise.resolve(tx_result);
        });
    }
    else {
      return result.data;
    }
  }).catch(error => {
    console.log(`get_transaction error ${error}`);
    if (error.response)
      return Promise.reject({
        message: error.message,
        data: error.response.data
      });
    else
      return Promise.reject(error);
  }).finally(() => {
    //console.log('job run finally');
  });
});

server.addMethod("get_microblock", async ([txid, network = default_network], serverParams) => {
  const api_endpoint = getStacksApiEndpoint(network, 1);
  return axios({
    method: 'GET',
    url: api_endpoint + '/microblock/unanchored/txs',
    headers: {
    },
    /* data to be sent, must be json */
    // data: {
    //   jobId: 1
    // }
  }).then(result => {
    return (result.data.results || []).filter(t => {
      return t.tx_id === ('0x' + txid).replace(/^0x0x/i,'0x');
    }).map(txInfo => {
      const runtime_cost = txInfo.execution_cost_read_count
        + txInfo.execution_cost_read_length
        + txInfo.execution_cost_runtime
        + txInfo.execution_cost_write_count
        + txInfo.execution_cost_write_length;
      const fee_rate = txInfo.fee_rate;
      const fee = fee_rate;
      return {
        sender_address: txInfo.sender_address,
        sponsor_address: txInfo.sponsor_address,
        fee_rate: txInfo.fee_rate,
        fee: fee,
        nonce: txInfo.nonce,
        sponsored: txInfo.sponsored,
        runtime_cost: runtime_cost,
        receipt_time: txInfo.receipt_time,
        receipt_time_iso: txInfo.receipt_time_iso,
        tx_id: txInfo.tx_id,
        tx_status: txInfo.tx_status,
        tx_result: txInfo.tx_result,
        events: txInfo.events,
        microblock: true,
      };
    })[0];
  }).catch(error => {
    console.log(`get_transaction error ${error}`);
    if (error.response)
      return Promise.reject({
        message: error.message,
        data: error.response.data
      });
    else
      return Promise.reject(error);
  }).finally(() => {
    //console.log('job run finally');
  });
});

server.addMethod("get_balances", async ([stxAddress, network], serverParams) => {
  const api_endpoint = stxAddress.match(/^SP/)
    ? getStacksApiEndpoint('mainnet', 1)
    : getStacksApiEndpoint(network || 'testnet', 1);

  return axios({
    method: 'GET',
    url: api_endpoint + '/address/' + stxAddress + "/balances",
    headers: {
    },
    /* data to be sent, must be json */
    // data: {
    //   jobId: 1
    // }
  }).then(result => {
    return result.data;
  }).catch(error => {
    console.log(`get_balances error ${error}`);
    if (error.response)
      return Promise.reject({
        message: error.message,
        data: error.response.data
      });
    else
      return Promise.reject(error);
  }).finally(() => {
    //console.log('job run finally');
  });
});

server.addMethod("get_transactions", async ([stxAddress, network], serverParams) => {
  const api_endpoint = stxAddress.match(/^SP/)
    ? getStacksApiEndpoint('mainnet', 1)
    : getStacksApiEndpoint(network || 'testnet', 1);

  return axios({
    method: 'GET',
    url: api_endpoint + '/address/' + stxAddress + "/transactions",
    headers: {
    },
    /* data to be sent, must be json */
    // data: {
    //   jobId: 1
    // }
  }).then(result => {
    return result.data;
  }).catch(error => {
    console.log(`get_transactions error ${error}`);
    if (error.response)
      return Promise.reject({
        message: error.message,
        data: error.response.data
      });
    else
      return Promise.reject(error);
  }).finally(() => {
    //console.log('job run finally');
  });
});

server.addMethod("faucet", async ([stxAddress, network], serverParams) => {
  const api_endpoint = stxAddress.match(/^SP/)
    ? getStacksApiEndpoint('mainnet', 1)
    : getStacksApiEndpoint(network || 'testnet', 1);

  return axios({
    method: 'POST',
    url: api_endpoint + 'faucets/stx?address=' + stxAddress,
    headers: {
    },
    /* data to be sent, must be json */
    // data: {
    //   jobId: 1
    // }
  }).then(result => {
    return result.data;
  }).catch(error => {
    console.log(`faucet error ${error}`);
    if (error.response)
      return Promise.reject({
        message: error.message,
        data: error.response.data
      });
    else
      return Promise.reject(error);
  }).finally(() => {
    //console.log('job run finally');
  });
});

server.addMethod("log", ({ message }) => console.log(message));

const app = express();
app.use(express.json());
app.use(express.urlencoded({ extended: false }));

app.get("/", (req, res) => {
  res.sendStatus(200);
});

app.post("/json-rpc", (req, res) => {
  const jsonRPCRequest = req.body;
  // server.receive takes a JSON-RPC request and returns a promise of a JSON-RPC response.
  // Alternatively, you can use server.receiveJSON, which takes JSON string as is (in this case req.body).
  server.receive(jsonRPCRequest, { a: 1, b: 2 })
    .then((jsonRPCResponse) => {
      if (jsonRPCResponse) {
        res.json(jsonRPCResponse);
      } else {
        // If response is absent, it was a JSON-RPC notification method.
        // Respond with no content status (204).
        res.sendStatus(204);
      }
    }).catch(err => {
      console.log(`server receive error ${err}`);
    });
  server.mapErrorToJSONRPCErrorResponse = (
    id,
    error
  ) => {
    return createJSONRPCErrorResponse(
      id,
      (error || {}).code || 0,
      (error || {}).message || "An unexpected error occurred",
      // Optional 4th argument. It maps to error.data of the response.
      error.data
    );
  };
});

app.listen(getEnv('PORT') || 5000);
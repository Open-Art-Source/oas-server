from flask import current_app as app, g
import uuid
import hashlib
import requests
from typing import Any, Dict, List, Union, NoReturn, Optional
from decimal import Decimal

from web3 import Web3
from web3._utils.filters import construct_event_filter_params
from web3._utils.events import get_event_data
from web3.datastructures import AttributeDict
from web3.exceptions import BlockNotFound
from eth_abi.codec import ABICodec
from oas.service.hdwallet import MINTER_WALLET, new_oas_address

import simplejson as json
import oas.config as oas_config

def deploy_chainlinkToken(gas_price):
    with app.open_resource('misc/bin/ChainlinkToken.abi',mode='rt') as f:
        with app.open_resource('misc/bin/ChainlinkToken.bin', mode='rt') as b:
            abi = f.read().replace('\n','').replace('\r','')
            bytecode = b.read().replace('\n','').replace('\r','')
            web3_rpc_endpoint = oas_config.get('WEB3_RPC_URL')
            w3 = Web3(Web3.HTTPProvider(web3_rpc_endpoint, request_kwargs={'timeout': 60}))
            chainId = w3.eth.chain_id
            contract = w3.eth.contract(abi=abi, bytecode=bytecode)
            contract_constructor = contract.constructor()
            address, dpath, private_key = MINTER_WALLET
            minter_address = Web3.toChecksumAddress(address)
            nonce = w3.eth.getTransactionCount(minter_address) 
            estimatedGas = contract_constructor.estimateGas({'from': address, 'value': 0})
            gas = estimatedGas + 50000
            currentGasPrice = w3.eth.gas_price
            gasPrice = w3.toWei(gas_price, 'gwei') if gas_price else currentGasPrice + w3.toWei(1, 'gwei')
            txn = contract_constructor.buildTransaction({'chainId':chainId, 'gas': gas, 'gasPrice': gasPrice, 'nonce': nonce})
            signed_txn = w3.eth.account.signTransaction(txn, private_key=private_key)
            tx_hash = signed_txn.hash.hex()
            txh = w3.eth.sendRawTransaction(signed_txn.rawTransaction).hex()
            return txh

def deploy_operatorFactory(linkTokenAddress, gas_price):
    with app.open_resource('misc/bin/contracts/chainlink/OperatorFactory.abi',mode='rt') as f:
        with app.open_resource('misc/bin/contracts/chainlink/OperatorFactory.bin', mode='rt') as b:
            abi = f.read().replace('\n','').replace('\r','')
            bytecode = b.read().replace('\n','').replace('\r','')
            web3_rpc_endpoint = oas_config.get('WEB3_RPC_URL')
            w3 = Web3(Web3.HTTPProvider(web3_rpc_endpoint, request_kwargs={'timeout': 60}))
            chainId = w3.eth.chain_id
            contract = w3.eth.contract(abi=abi, bytecode=bytecode)
            linkToken = linkTokenAddress or oas_config.get('OAS_CHAINLINK_TOKEN_ADDRESS')
            contract_constructor = contract.constructor(Web3.toChecksumAddress(linkToken))
            address, dpath, private_key = MINTER_WALLET
            minter_address = Web3.toChecksumAddress(address)
            nonce = w3.eth.getTransactionCount(minter_address) 
            estimatedGas = contract_constructor.estimateGas({'from': address, 'value': 0})
            gas = estimatedGas + 50000
            currentGasPrice = w3.eth.gas_price
            gasPrice = w3.toWei(gas_price, 'gwei') if gas_price else currentGasPrice + w3.toWei(1, 'gwei')
            txn = contract_constructor.buildTransaction({'chainId':chainId, 'gas': gas, 'gasPrice': gasPrice, 'nonce': nonce})
            signed_txn = w3.eth.account.signTransaction(txn, private_key=private_key)
            tx_hash = signed_txn.hash.hex()
            txh = w3.eth.sendRawTransaction(signed_txn.rawTransaction).hex()
            return txh

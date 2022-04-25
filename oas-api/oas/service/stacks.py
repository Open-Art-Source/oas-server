from typing import Any, Dict, List, Union, NoReturn, Optional
import simplejson as json
import re
import os
import requests
import oas.config as oas_config

default_network = oas_config.get('STACKS_NETWORK') or 'testnet'

def get_balances(address:str, network:str = None) -> Any:
    oas_stacks_api_endpoint = oas_config.get('OAS_STACKS_RPC_URL')
    json_rpc = {
        'id': '1',
        'jsonrpc': "2.0",
        'method': "get_balances",
        'params': [address, network or default_network]
        }
    payload = json.dumps(json_rpc)
    response = requests.post(oas_stacks_api_endpoint, json=json_rpc)
    result = response.json()
    return result

def get_transaction(txid:str, network:str = None) -> Any:
    oas_stacks_api_endpoint = oas_config.get('OAS_STACKS_RPC_URL')
    json_rpc = {
        'id': '1',
        'jsonrpc': "2.0",
        'method': "get_transaction",
        'params': [txid, network or default_network]
        }
    payload = json.dumps(json_rpc)
    response = requests.post(oas_stacks_api_endpoint, json=json_rpc)
    result = response.json()
    return result

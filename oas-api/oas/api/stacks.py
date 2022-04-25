from flask import current_app as app, g
from flask_jsonrpc import JSONRPCBlueprint
from typing import Any, Dict, List, Union, NoReturn, Optional
from oas.api import AuthorizationView
from oas.service.stacks import get_balances, get_transaction
import simplejson as json
import re
import os
import requests
import oas.config as oas_config

stacks = JSONRPCBlueprint('stacks', __name__, jsonrpc_site_api=AuthorizationView)

@stacks.method('get_balances')
def _get_balances(address:str, network:str = None) -> Any:
    return get_balances(address, network)

    oas_stacks_api_endpoint = oas_config.get('OAS_STACKS_RPC_URL')
    json_rpc = {
        'id': '1',
        'jsonrpc': "2.0",
        'method': "get_balances",
        'params': [address, network]
        }
    payload = json.dumps(json_rpc)
    response = requests.post(oas_stacks_api_endpoint, json=json_rpc)
    result = response.json()
    return result

@stacks.method('get_transaction')
def _get_transaction(txid:str, network:str = None) -> Any:
    return get_transaction(txid, network)

    oas_stacks_api_endpoint = oas_config.get('OAS_STACKS_RPC_URL')
    json_rpc = {
        'id': '1',
        'jsonrpc': "2.0",
        'method': "get_transaction",
        'params': [txid, network]
        }
    payload = json.dumps(json_rpc)
    response = requests.post(oas_stacks_api_endpoint, json=json_rpc)
    result = response.json()
    return result

@stacks.method('faucet')
def faucet(address:str, network:str = None) -> Any:
    oas_stacks_api_endpoint = oas_config.get('OAS_STACKS_RPC_URL')
    json_rpc = {
        'id': '1',
        'jsonrpc': "2.0",
        'method': "faucet",
        'params': [address, network]
        }
    payload = json.dumps(json_rpc)
    response = requests.post(oas_stacks_api_endpoint, json=json_rpc)
    result = response.json()
    return result

from flask import current_app as app, g
import uuid
import hashlib
from typing import Any, Dict, List, Union, NoReturn, Optional
from decimal import Decimal
from sqlalchemy import or_, and_
from oas.model.person import Person
from oas.model.artist import Artist
from oas.model.artwork import Artwork
from oas.model.non_fungible_token import NftToken
from oas.model.ownership import Ownership
from oas.model.person import Person
from oas.model.listing import Listing
from oas.model.listing_price import ListingPrice

from web3 import Web3
from web3._utils.filters import construct_event_filter_params
from web3._utils.events import get_event_data
from web3.datastructures import AttributeDict
from web3.exceptions import BlockNotFound
from eth_abi.codec import ABICodec
import oas.config as oas_config
from oas.exception import NotOwnerException
from oas.service.hdwallet import MINTER_WALLET, new_oas_address
from oas.service.stacks import get_transaction, get_balances
from oas.service.artist import collect_nft_token
import requests
import simplejson as json

def _get_user_id(claims: dict) -> str:
    user_id = claims['user_id']
    user_id_hash = hashlib.sha256(user_id.encode('utf-8')).hexdigest()
    return user_id_hash

def load_user_context(claims: dict) -> Any:
    session = app.db_session
    user_id_hash = _get_user_id(claims)
    users = session.query(Person).filter(Person.oauth_id == 'firebase:' + user_id_hash)
    g.user = users.first()
    return g.user

def register(first_name: str, last_name: str, claims: Dict, is_artist: Optional[bool] = True, commit: Optional[bool] = True) -> Any:
    user = load_user_context(claims)
    if not user:
        user_id_hash = _get_user_id(claims)
        user = Person(person_id=uuid.uuid4(), first_name=first_name, last_name = last_name, oauth_id="firebase:" + user_id_hash)
        session = app.db_session
        session.add(user)
        if is_artist: session.add(Artist(person=user))
        if commit: session.commit()
    return user

def create_stx_wallet(password):
    user = g.user
    oas_stacks_api_endpoint = oas_config.get('OAS_STACKS_RPC_URL')
    stx_password = hashlib.sha256(password.encode('utf-8')).hexdigest()
    if not user.stx_address:
        json_rpc = {
            'id': '1',
            'jsonrpc': "2.0",
            'method': "create_wallet",
            'params': [stx_password]
            }
        payload = json.dumps(json_rpc)
        result = requests.post(oas_stacks_api_endpoint, json=json_rpc)
        stx_wallet = result.json()
        session = app.db_session
        user.stx_secret = stx_wallet['result']['secret']
        user.stx_address = stx_wallet['result']['testnetAddress']
        session.add(user)
        session.commit()
    return {'stx_address': user.stx_address}

def list_artwork(filter: dict, commit: Optional[bool]=True) -> Any:
    artwork_id = filter.get('artwork_id')
    person_id = filter.get('person_id') 
    listing_id = filter.get('listing_id')
    price_id = filter.get('price_id')
    currency = filter.get('currency')
    amount = filter.get('amount')
    active = filter.get('active')
    was_active = None
    old_amount = None
    def get_current_owner(o):
        return not o.end_date

    def get_listing(l):
        return l.active and l.listing_id == listing_id

    session = app.db_session
    artworks = [ a for a in session.query(Artwork).filter(and_(Artwork.artwork_id == artwork_id)) ]

    if not artworks:
        raise Exception('artwork not found')

    if active and not artworks[0].stx_contract_address:
        raise Exception('nft not minted yet')
    
    if artworks[0].stx_contract_address and not artworks[0].stx_token_id:
        token = collect_nft_token(dict(artwork_id = artwork_id))
        token_id = token['token_id'] if token else None
        if active and not token_id: raise Exception('nft token is still minting')


    owner = [ o for o in (artworks[0].ownership or [] if artworks else []) if not o.end_date and o.person_id == person_id ]
    if not owner:
        raise NotOwnerException('not owner')
    
    listing = [ l for l in (owner[0].listing or [] if owner else []) ]
    currency = 'STX' if not currency else currency
    purchase = None
    listing_price = [ p for p in (listing[0].listing_price or [] if listing else []) if p.price_id == price_id or p.currency == currency ]
    if not listing:
        listing = Listing.from_dict(dict(ownership_id = owner[0].ownership_id, artwork_id = artwork_id, person_id = person_id, active = active ))
        session.add(listing)
    else:
        listing = listing[0]
        was_active = listing.active
        purchase = listing.purchase
        if not purchase:
            listing.active = active if active is not None else listing.active
    
    if listing_price:
        old_amount = listing_price[0].amount
        if not purchase:
            listing_price[0].amount = amount if amount != None else old_amount
        amount = listing_price[0].amount        
    elif currency and amount:
        item_price = ListingPrice.from_dict(dict(listing_id = listing.listing_id, currency = currency, amount = amount))
        listing.listing_price.append(item_price)
        listing_price = listing.listing_price

    if currency == 'STX' and artworks:
        user = g.user
        artwork = artworks[0]
        stx_token_id = artwork.stx_token_id
        stx_contract_address = artwork.stx_contract_address
        stx_secret = user.stx_secret
        stx_address = user.stx_address
        wallet_address, d_path, private_key = new_oas_address(str(person_id), use_ex_priv=True)
        oas_stacks_api_endpoint = oas_config.get('OAS_STACKS_RPC_URL')
        sip009_address = oas_config.get('OAS_STACKS_NFT_CONTRACT')            
        stx_password = hashlib.sha256(private_key.encode('utf-8')).hexdigest()
        stx_amount = amount * 1000000
        old_tx_hash = listing_price[0].tx_hash
        old_status = listing_price[0].status or 0
        if old_tx_hash and (old_status == 1 or old_status == 4):
            tx_result = get_transaction(old_tx_hash)
            result = tx_result.get('result')
            error = tx_result.get('error')
            if result:
                tx_status = result['tx_status']
                if tx_status == 'success':
                    listing_price[0].status = 2 if old_status == 1 else 5
                    old_status = listing_price[0].status or 0
                elif tx_status != 'pending':
                    listing_price[0].status = 3 if old_status == 1 else 6
                    old_status = listing_price[0].status or 0
                else:
                    #listing.status = False
                    pass
            elif error:
                if '404' in error['message']:
                    listing_price[0].status = 0


        if (active and (not purchase) and ((not was_active or float(old_amount) != amount or old_status in [0, 3, 6]))):
            json_rpc = {
                'id': '1',
                'jsonrpc': "2.0",
                'method': "list_nft_token",
                'params': [stx_address, stx_token_id, stx_amount, stx_secret, stx_password]
                }
            payload = json.dumps(json_rpc)
            response = requests.post(oas_stacks_api_endpoint, json=json_rpc)
            result = response.json()
            tx_result = result.get('result')
            if tx_result:
                tx_hash = tx_result['txid']
                listing_price[0].tx_hash = tx_hash
                listing_price[0].status = 1
            else: raise Exception(result.get('error'))
        elif not active and (not purchase) and (was_active or old_status in [2]):
            if old_status == 2:
                json_rpc = {
                    'id': '1',
                    'jsonrpc': "2.0",
                    'method': "delist_nft_token",
                    'params': [stx_address, stx_token_id, stx_secret, stx_password]
                    }
                payload = json.dumps(json_rpc)
                response = requests.post(oas_stacks_api_endpoint, json=json_rpc)
                result = response.json()
                tx_result = result.get('result')
                if tx_result:
                    tx_hash = tx_result['txid']
                    listing_price[0].tx_hash = tx_hash
                    listing_price[0].status = 4
                else: raise Exception(result.get('error'))
            else:
                listing_price[0].status = 0
    if commit:
        session.commit()
    if purchase:
        raise Exception('someone purchase this, cannot change listing state')

    return listing, listing_price

def deploy_erc721(gas_price):
    with app.open_resource('misc/bin/contracts/L1ERC721V1.abi',mode='rt') as f:
        with app.open_resource('misc/bin/contracts/L1ERC721V1.bin', mode='rt') as b:
            abi = f.read().replace('\n','').replace('\r','')
            bytecode = b.read().replace('\n','').replace('\r','')
            web3_rpc_endpoint = oas_config.get('WEB3_RPC_URL')
            w3 = Web3(Web3.HTTPProvider(web3_rpc_endpoint, request_kwargs={'timeout': 60}))
            chainId = w3.eth.chain_id
            erc721 = w3.eth.contract(abi=abi, bytecode=bytecode)
            erc721_constructor = erc721.constructor()
            address, dpath, private_key = MINTER_WALLET
            minter_address = Web3.toChecksumAddress(address)
            nonce = w3.eth.getTransactionCount(minter_address) 
            estimatedGas = erc721_constructor.estimateGas({'from': address, 'value': 0})
            gas = estimatedGas + 50000
            currentGasPrice = w3.eth.gas_price
            gasPrice = w3.toWei(gas_price, 'gwei') if gas_price else currentGasPrice + w3.toWei(1, 'gwei')
            txn = erc721_constructor.buildTransaction({'chainId':chainId, 'gas': gas, 'gasPrice': gasPrice, 'nonce': nonce})
            signed_txn = w3.eth.account.signTransaction(txn, private_key=private_key)
            tx_hash = signed_txn.hash.hex()
            txh = w3.eth.sendRawTransaction(signed_txn.rawTransaction).hex()
            return txh

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

def erc721_check(address=None):
    with app.open_resource('misc/bin/contracts/L1ERC721V1.abi',mode='rt') as f:
        abi = f.read().replace('\n','').replace('\r','')
        web3_rpc_endpoint = oas_config.get('WEB3_RPC_URL')
        w3 = Web3(Web3.HTTPProvider(web3_rpc_endpoint, request_kwargs={'timeout': 60}))
        chainId = w3.eth.chain_id
        erc721_address = Web3.toChecksumAddress(oas_config.get('NFT_TOKEN_ADDRESS'))  
        nft = w3.eth.contract(address=erc721_address, abi=abi)
        name = nft.functions.name().call()
        symbol = nft.functions.symbol().call()
        return dict(symbol=symbol, name=name, address=erc721_address)

def deploy_erc1967Proxy(gas_price, proxied_abi = None, proxied_address = None):
    proxied_abi = proxied_abi or 'misc/bin/contracts/L1ERC721V1.abi'
    proxied_address = Web3.toChecksumAddress(proxied_address or oas_config.get('NFT_TOKEN_IMPLEMENTATION_ADDRESS'))
    with app.open_resource('misc/bin/contracts/ERC1967Proxy.abi',mode='rt') as f:
        with app.open_resource('misc/bin/contracts/ERC1967Proxy.bin', mode='rt') as b:
            with app.open_resource(proxied_abi, mode='rt') as i:
                abi = f.read().replace('\n','').replace('\r','')
                proxied_abi = i.read().replace('\n','').replace('\r','')
                bytecode = b.read().replace('\n','').replace('\r','')
                web3_rpc_endpoint = oas_config.get('WEB3_RPC_URL')
                w3 = Web3(Web3.HTTPProvider(web3_rpc_endpoint, request_kwargs={'timeout': 60}))
                chainId = w3.eth.chain_id
                proxied = w3.eth.contract(abi=proxied_abi)
                proxied_initialize = proxied.functions.initialize('oas nft', 'oas','https://ipfs.io/ipfs')
                initialize = proxied_initialize.buildTransaction({'to':proxied_address})
                initialized_txdata = initialize['data']
                erc1967 = w3.eth.contract(abi=abi, bytecode=bytecode)
                erc1967_constructor = erc1967.constructor(proxied_address, initialized_txdata)
                address, dpath, private_key = MINTER_WALLET
                minter_address = Web3.toChecksumAddress(address)
                nonce = w3.eth.getTransactionCount(minter_address) 
                estimatedGas = erc1967_constructor.estimateGas({'from': address, 'value': 0})
                gas = estimatedGas + 50000
                currentGasPrice = w3.eth.gas_price
                gasPrice = w3.toWei(gas_price, 'gwei') if gas_price else currentGasPrice + w3.toWei(1, 'gwei')
                txn = erc1967_constructor.buildTransaction({'chainId':chainId, 'gas': gas, 'gasPrice': gasPrice, 'nonce': nonce})
                signed_txn = w3.eth.account.signTransaction(txn, private_key=private_key)
                tx_hash = signed_txn.hash.hex()
                txh = w3.eth.sendRawTransaction(signed_txn.rawTransaction).hex()
                return txh

def send_erc20(to:str, val:float, contract_address:str = None, decimal:int = 18, nonce:int=None, gas_price=None):
    with app.open_resource('misc/bin/ChainlinkToken.abi',mode='rt') as f:
        abi = f.read().replace('\n','').replace('\r','')
        web3_rpc_endpoint = oas_config.get('WEB3_RPC_URL')
        w3 = Web3(Web3.HTTPProvider(web3_rpc_endpoint, request_kwargs={'timeout': 60}))
        chainId = w3.eth.chain_id
        contract = w3.eth.contract(address=Web3.toChecksumAddress(contract_address or oas_config.get('OAS_CHAINLINK_TOKEN_ADDRESS')), abi=abi)
        address, dpath, private_key = MINTER_WALLET
        from_address = Web3.toChecksumAddress(address)
        nonce = w3.eth.getTransactionCount(from_address) 
        to_address = Web3.toChecksumAddress(to)
        amount = Web3.toWei(val, 'ether') 
        func = contract.functions.transfer(to_address, amount)
        estimatedGas = func.estimateGas({'from': address, 'value': 0})
        gas = estimatedGas + 50000
        currentGasPrice = w3.eth.gas_price
        gasPrice = w3.toWei(gas_price, 'gwei') if gas_price else currentGasPrice + w3.toWei(1, 'gwei')
        txn = func.buildTransaction({'chainId':chainId, 'gas': gas, 'gasPrice': gasPrice, 'nonce': nonce})
        signed_txn = w3.eth.account.signTransaction(txn, private_key=private_key)
        tx_hash = signed_txn.hash.hex()
        txh = w3.eth.sendRawTransaction(signed_txn.rawTransaction).hex()
        return txh

def send_eth(to:str, val:float, nonce:int=None, gas_price=None):
    web3_rpc_endpoint = oas_config.get('WEB3_RPC_URL')
    w3 = Web3(Web3.HTTPProvider(web3_rpc_endpoint, request_kwargs={'timeout': 60}))
    chainId = w3.eth.chain_id
    address, dpath, private_key = MINTER_WALLET
    minter_address = Web3.toChecksumAddress(address)
    nonce = nonce or w3.eth.getTransactionCount(minter_address) 
    amount = Web3.toWei(val, 'ether')
    estimatedGas = 21000
    currentGasPrice = w3.eth.gas_price
    gasPrice = w3.toWei(gas_price, 'gwei') if gas_price else currentGasPrice + w3.toWei(1, 'gwei')
    signed_txn = w3.eth.account.signTransaction(dict(to=to, value=amount, gas = estimatedGas, gasPrice=gasPrice, nonce=nonce, chainId=chainId), private_key=private_key)
    tx_hash = signed_txn.hash.hex()
    txh = w3.eth.sendRawTransaction(signed_txn.rawTransaction).hex()
    return txh

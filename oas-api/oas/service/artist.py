from flask import current_app as app, g
from io import BytesIO
import uuid
import hashlib
import re
from typing import Any, Dict, List, Union, NoReturn, Optional
from sqlalchemy import or_, and_
from oas.model.artist import Artist
from oas.model.artwork import Artwork
from oas.model.non_fungible_token import NftToken
from oas.model.ownership import Ownership
from oas.model.person import Person
from oas.model.listing import Listing
from oas.model.listing_price import ListingPrice
from oas.service.hdwallet import MINTER_WALLET
from oas.service.hdwallet import new_oas_address, new_hdwallet, make_subwallet
from web3 import Web3
from web3._utils.filters import construct_event_filter_params
from web3._utils.events import get_event_data
from web3.datastructures import AttributeDict
from web3.exceptions import BlockNotFound
from eth_abi.codec import ABICodec
from oas.exception import NotOwnerException
from oas.service.storage import cloud_save, FileObject
import oas.config as oas_config
import simplejson as json
import requests

def _check_owner(artwork:Artwork, blocked:bool = True) -> bool:
    user = g.user
    person_id = user.person_id
    owner = [ o for o in (artwork.ownership) if not o.end_date and o.person_id == person_id ]
    if not owner:
        raise NotOwnerException('not owner')
    return True

def get_artwork(filter: dict) -> Any:
    artwork_id = filter.get('artwork_id')
    artist_id = filter.get('artist_id')
    person_id = filter.get('person_id')
    session = app.db_session
    artworks = session.query(Artwork).outerjoin(Artwork.ownership).filter(
                                        and_(
                                            or_(Artwork.artwork_id == artwork_id, not artwork_id)
                                            ,or_(Artwork.artist_id == artist_id, not artist_id)
                                            ,or_(and_(Ownership.person_id == person_id, not Ownership.end_date) , not person_id)
                                            )
                                        )
    return artworks

def register_artwork(artist: Artist, artwork: Artwork, commit: Optional[bool]=True) -> Any:
    session = app.db_session
    artwork_id = artwork.artwork_id
    old_artwork = artwork_id and get_artwork(dict(artwork_id=artwork_id)).first()
    if not old_artwork:
        artist.artwork.append(artwork)
        # do not do link here for ownership(many to many), don't work due to
        # the artist thing, caused circular dependency
    else:
        _check_owner(old_artwork)
        session.merge(artwork)
    session.add(artist)
    if commit: 
        session.commit()
        if not old_artwork:
            person = artist.person
            # must be done here to get around circulation problem of
            # sqlalchmey, WTF!
            # the commit create the necessary records, below is effectively a
            # 'link' after create
            # and don't need to add, to the parent/child as per doc, truly
            # alchemy(black magic, again WTF)
            owner = Ownership.from_dict(dict(person=person, artwork=artwork))
            session.flush()
    return artwork

def delete_artwork(filter: dict, commit: Optional[bool]=True) -> Any:
    session = app.db_session
    artwork_id = filter.get('artwork_id')
    artist_id = filter.get('artist_id')
    artworks = session.query(Artwork).filter(and_(Artwork.artwork_id == artwork_id, Artwork.artist_id == artist_id))
    old_artwork = artworks.first()
    if old_artwork:
        _check_owner(old_artwork)
        session.delete(old_artwork)
        if commit: session.commit()
        return True
    return False

def make_nft_token(filter: dict, gas_price:int=None, commit: Optional[bool]=True) -> Any:
    session = app.db_session
    artwork_id = filter.get('artwork_id')
    artist_id = filter.get('artist_id') 
    re_mint = filter.get('re_mint')
    token_type = filter.get('token') if filter.get('token') != None else 'STX'
    stx = 'STX' == token_type

    artworks = session.query(Artwork).filter(
            and_(
            Artwork.artwork_id == artwork_id
            , Artwork.artist_id == artist_id
            )
            )
    old_artwork = artworks.first()
    nft_token = None
    minted = None
    minting = None
    token = None
    if old_artwork:

        for nft_token in old_artwork.non_fungible_token:
            tx_hash = nft_token.tx_hash
            token_id = nft_token.token_id
            contract_address = nft_token
            if tx_hash and nft_token.blockchain == token_type and not nft_token.token_id:
                minting = True
                token = collect_nft_token(filter, commit)
                if token and token['token_id']: 
                    minted = True
                    return token

        if minting and token and not re_mint: return token

        _check_owner(old_artwork)
        
        erc721_address = Web3.toChecksumAddress(oas_config.get('NFT_TOKEN_ADDRESS'))  

        artwork_owner_address = filter.get('owner_wallet_address')
        image_files_hash = old_artwork.image_files_hash
        primary_image_file_name = old_artwork.primary_image_file_name
        ipfs_endpoint = oas_config.get('IPFS_API_URL')
        erc721_metadata = dict(artwork_id = old_artwork.artwork_id,
            name = old_artwork.title,
            description = old_artwork.description or old_artwork.title,
            image = f"https://ipfs.io/ipfs/{image_files_hash}/{primary_image_file_name}")
        
        cloud_file = cloud_save([FileObject(file = BytesIO(bytes(json.dumps(erc721_metadata),'utf8')), filename='metadata.json')])
        folder = cloud_file[-1]
        ipfs_hash = folder["Hash"]

        token_uri = f"https://ipfs.io/ipfs/{ipfs_hash}/metadata.json"

        if stx:
            user = g.user
            person_id = user.person_id
            stx_secret = user.stx_secret
            wallet_address, d_path, private_key = new_oas_address(str(person_id), use_ex_priv=True)
            oas_stacks_api_endpoint = oas_config.get('OAS_STACKS_RPC_URL')
            sip009_address = oas_config.get('OAS_STACKS_NFT_CONTRACT')

            stx_password = hashlib.sha256(private_key.encode('utf-8')).hexdigest()
            json_rpc = {
                'id': '1',
                'jsonrpc': "2.0",
                'method': "mint_nft_token",
                'params': [token_uri, stx_secret, stx_password, dict(booster = 4 if re_mint else 1)]
                }
            payload = json.dumps(json_rpc)
            response = requests.post(oas_stacks_api_endpoint, json=json_rpc)
            result = response.json()
            if result.get('result'):
                tx_hash = '0x' + result['result']['txid']
                mint_result = dict(contract_address = sip009_address, tx_hash = tx_hash, blockchain='STX')
                nft_token = NftToken.from_dict(mint_result)
                old_token = [ t for t in old_artwork.non_fungible_token if t.contract_address == sip009_address and t.tx_hash == tx_hash ]
                if not old_token:
                    old_artwork.stx_contract_address = sip009_address
                    old_artwork.non_fungible_token.append(nft_token)
                    if commit: session.commit()
                return mint_result
            else:
                raise Exception(result)
        else:
            with app.open_resource('misc/bin/L1ERC721.abi',mode='rt') as f:
                abi = f.read().replace('\n','').replace('\r','')
                web3_rpc_endpoint = oas_config.get('WEB3_RPC_URL')
                w3 = Web3(Web3.HTTPProvider(web3_rpc_endpoint, request_kwargs={'timeout': 60}))
                chainId = w3.eth.chain_id
                nft = w3.eth.contract(address=erc721_address, abi=abi)
                address, dpath, private_key = MINTER_WALLET
                minter_address = Web3.toChecksumAddress(address)
                nonce = w3.eth.getTransactionCount(minter_address) 
                mint_to = artwork_owner_address
                offchain_id = Web3.keccak(text=artwork_id)
                id = Web3.toInt(offchain_id)
                mint = nft.functions.mint(mint_to, token_uri, id)
                estimatedGas = mint.estimateGas({'from': address, 'value': 0})
                gas = estimatedGas + 50000
                currentGasPrice = w3.eth.gas_price
                gasPrice = w3.toWei(gas_price, 'gwei') if gas_price else currentGasPrice + w3.toWei(1, 'gwei')
                txn = mint.buildTransaction({'chainId':chainId, 'gas': gas, 'gasPrice': gasPrice, 'nonce': nonce})
                signed_txn = w3.eth.account.signTransaction(txn, private_key=private_key)
                tx_hash = signed_txn.hash.hex()
                w3.eth.sendRawTransaction(signed_txn.rawTransaction) 
                if not nft_token:
                    nft_token = NftToken.from_dict(dict(contract_address = erc721_address, tx_hash = tx_hash))
                    old_artwork.nft_contract_address = erc721_address
                    old_artwork.non_fungible_token.append(nft_token)
                else:
                    nft_token.tx_hash = tx_hash
                if commit: session.commit()
                return dict(contract_address = erc721_address, tx_hash = tx_hash)

def check_token_status(token, commit: Optional[bool]=True) -> Any:
    
    session = app.db_session
    user = g.user

    if token:
        stx = token.blockchain == 'STX'
        if stx:
            person_id = user.person_id
            tx_hash = token.tx_hash
            stx_secret = user.stx_secret
            oas_stacks_api_endpoint = oas_config.get('OAS_STACKS_RPC_URL')
            sip009_address = oas_config.get('OAS_STACKS_NFT_CONTRACT')
            json_rpc = {
                'id': '1',
                'jsonrpc': "2.0",
                'method': "get_transaction",
                'params': [tx_hash]
                }
            response = requests.post(oas_stacks_api_endpoint, json=json_rpc)
            result = response.json()
            tx_result = result['result']
            status = tx_result['tx_status']
            if status == "success":
                for event in tx_result['events']:
                    event_type = event['event_type']
                    asset = event['asset']
                    if event_type == 'non_fungible_token_asset' and asset['recipient'] == user.stx_address:
                        token_id = asset['value']['repr']
                        token.token_id = re.sub('^u','',token_id)
                        token.artwork.stx_token_id = token.token_id
                        token.artwork.stx_contract_address = sip009_address
                        if commit: session.commit()
                        break
            return token and token.to_dict()
        else:
            with app.open_resource('misc/ERC721.abi',mode='rt') as f:
                abi = f.read().replace('\n','').replace('\r','')
                web3_rpc_endpoint = oas_config.get('WEB3_RPC_URL')
                w3 = Web3(Web3.HTTPProvider(web3_rpc_endpoint, request_kwargs={'timeout': 60}))
                chainId = w3.eth.chain_id
                erc721_address = Web3.toChecksumAddress(oas_config.get('NFT_TOKEN_ADDRESS'))  
                nft = w3.eth.contract(address=erc721_address, abi=abi)
                offchain_id = Web3.keccak(text=artwork_id)
                id = Web3.toInt(offchain_id)
                minted = nft.events.Minted.createFilter(fromBlock='earliest', toBlock='latest', argument_filters={"offchainId": id})
                logs = minted.get_all_entries()
                for log in logs:
                    x = dict(log)
                    tx_hash = log.transactionHash.hex()
                    token_id = log['args']['tokenId']
                    if tx_hash == token.tx_hash:
                        token.token_id = str(token_id)
                        token.artwork.nft_token_id = str(token_id)
                        token.artwork.nft_contract_address = erc721_address

                if commit and logs: session.commit()
                return token and token.to_dict()
    else:
        tokens = session.query(NftToken).filter(and_(NftToken.artwork_id == artwork_id))
        token = tokens.first()
        return token and token.to_dict()

def collect_nft_token(filter: dict, commit: Optional[bool]=True) -> Any:
    session = app.db_session
    user = g.user
    artwork_id = filter.get('artwork_id')
    artist_id = filter.get('artist_id')  
    tx_hash = filter.get('tx_hash') or None
    artwork_owner_address = filter.get('owner_wallet_address')
    tokens = session.query(NftToken).join(Artwork).filter(
                                                and_(
                                                   NftToken.artwork_id == artwork_id
                                                 , or_(
                                                     and_(NftToken.token_id == None, tx_hash == None)
                                                    , and_(NftToken.token_id != None, NftToken.status == None)
                                                    , and_(NftToken.tx_hash == tx_hash, tx_hash != None)
                                                    )
                                                 )
                                                )
    for token in tokens:
        t = check_token_status(token)
        if t['token_id']: return t

    token = tokens.first()
    return token.to_dict() if token else None


def transfer_nft_token(owner:Person, to: str, token_id:str, filter: dict, gas_price:int=None, commit: Optional[bool]=True) -> Any:
    session = app.db_session
    artwork_id = filter.get('artwork_id')
    artist_id = filter.get('artist_id')    
    artwork_owner_address = filter.get('owner_wallet_address')
    tokens = session.query(NftToken).filter(and_(NftToken.artwork_id == artwork_id, NftToken.token_id == token_id))
    token = tokens.first()
    if token:
        artwork = token.artwork
        _check_owner(artwork)
        with app.open_resource('misc/ERC721.abi',mode='rt') as f:
            abi = f.read().replace('\n','').replace('\r','')
            web3_rpc_endpoint = oas_config.get('WEB3_RPC_URL')
            w3 = Web3(Web3.HTTPProvider(web3_rpc_endpoint, request_kwargs={'timeout': 60}))
            chainId = w3.eth.chain_id
            erc721_address = Web3.toChecksumAddress(oas_config.get('NFT_TOKEN_ADDRESS'))  
            nft = w3.eth.contract(address=erc721_address, abi=abi)
            offchain_id = Web3.keccak(text=artwork_id)
            id = Web3.toInt(text=token_id)
            person_id = owner.person_id
            wallet_address, d_path, private_key = new_oas_address(str(person_id), use_ex_priv=True)
            minter_address, dpath, minter_private_key = MINTER_WALLET
            nonce = w3.eth.getTransactionCount(wallet_address if gas_price != 0 else minter_address) 
            safeTransferFrom = nft.functions.safeTransferFrom(wallet_address, to, id)
            estimatedGas = safeTransferFrom.estimateGas({'from': wallet_address, 'value': 0})
            gas = estimatedGas + 50000
            currentGasPrice = w3.eth.gas_price
            gasPrice = w3.toWei(gas_price, 'gwei') if gas_price else currentGasPrice + w3.toWei(1, 'gwei')
            txn = safeTransferFrom.buildTransaction({'chainId':chainId, 'gas': gas, 'gasPrice': gasPrice, 'nonce': nonce})
            signed_txn = w3.eth.account.signTransaction(txn, private_key=private_key if gas_price != 0 else minter_private_key)
            tx_hash = signed_txn.hash.hex()
            w3.eth.sendRawTransaction(signed_txn.rawTransaction) 
            #should delete token ?
            #if commit: session.commit()
            return tx_hash
    else:
        pass

def raw_transfer_nft_token(owner:Person, to: str, token_id:str, erc721_address:str=None, gas_price:int=None, commit: Optional[bool]=True) -> Any:
    session = app.db_session
    with app.open_resource('misc/ERC721.abi',mode='rt') as f:
        abi = f.read().replace('\n','').replace('\r','')
        web3_rpc_endpoint = oas_config.get('WEB3_RPC_URL')
        w3 = Web3(Web3.HTTPProvider(web3_rpc_endpoint, request_kwargs={'timeout': 60}))
        chainId = w3.eth.chain_id
        erc721_address = erc721_address or Web3.toChecksumAddress(oas_config.get('NFT_TOKEN_ADDRESS'))  
        nft = w3.eth.contract(address=erc721_address, abi=abi)
        id = Web3.toInt(text=token_id)
        person_id = owner.person_id
        wallet_address, d_path, private_key = new_oas_address(str(person_id), use_ex_priv=True)
        minter_address, dpath, minter_private_key = MINTER_WALLET
        nonce = w3.eth.getTransactionCount(wallet_address if gas_price != 0 else minter_address) 
        action = nft.functions.safeTransferFrom(wallet_address, to, id)
        estimatedGas = action.estimateGas({'from': wallet_address, 'value': 0})
        gas = estimatedGas + 50000
        currentGasPrice = w3.eth.gas_price
        gasPrice = w3.toWei(gas_price, 'gwei') if gas_price else currentGasPrice + w3.toWei(1, 'gwei')
        txn = action.buildTransaction({'chainId':chainId, 'gas': gas, 'gasPrice': gasPrice, 'nonce': nonce})
        signed_txn = w3.eth.account.signTransaction(txn, private_key=private_key if gas_price != 0 else minter_private_key)
        tx_hash = signed_txn.hash.hex()
        w3.eth.sendRawTransaction(signed_txn.rawTransaction) 
        #should delete token ?
        #if commit: session.commit()
        return tx_hash

def get_nft_token(filter:dict, token_id:str=None) -> Any:
    session = app.db_session
    artwork_id = filter.get('artwork_id')
    artist_id = filter.get('artist_id')    
    tokens = session.query(NftToken).filter(and_(NftToken.artwork_id == artwork_id))
    token = tokens.first()
    if token:
        with app.open_resource('misc/ERC721.abi',mode='rt') as f:
            abi = f.read().replace('\n','').replace('\r','')
            web3_rpc_endpoint = oas_config.get('WEB3_RPC_URL')
            w3 = Web3(Web3.HTTPProvider(web3_rpc_endpoint, request_kwargs={'timeout': 60}))
            erc721_address = Web3.toChecksumAddress(oas_config.get('NFT_TOKEN_ADDRESS'))  
            nft = w3.eth.contract(address=erc721_address, abi=abi)
            id = Web3.toInt(text=(token_id if token_id else token.token_id))
            ownerOf = nft.functions.ownerOf(id)
            owner = ownerOf.call()
            tokenURI = nft.functions.tokenURI(id)
            tokenUrl = tokenURI.call()
            tokenMeta = requests.get(tokenUrl).json()
            return dict(owner=owner, tokenUrl=tokenUrl, tokenMeta = tokenMeta)
    else:
        tokens = session.query(NftToken).filter(and_(NftToken.artwork_id == artwork_id))
        token = tokens.first()
        return token

def nft_token_info(token_id:str, erc721_address:str=None) -> Any:
    with app.open_resource('misc/ERC721.abi',mode='rt') as f:
        abi = f.read().replace('\n','').replace('\r','')
        web3_rpc_endpoint = oas_config.get('WEB3_RPC_URL')
        w3 = Web3(Web3.HTTPProvider(web3_rpc_endpoint, request_kwargs={'timeout': 60}))
        erc721_address = erc721_address or Web3.toChecksumAddress(oas_config.get('NFT_TOKEN_ADDRESS'))  
        nft = w3.eth.contract(address=erc721_address, abi=abi)
        id = Web3.toInt(text=(token_id if token_id else token.token_id))
        ownerOf = nft.functions.ownerOf(id)
        owner = ownerOf.call()
        tokenURI = nft.functions.tokenURI(id)
        tokenUrl = tokenURI.call()
        tokenMeta = requests.get(tokenUrl).json()
        return dict(owner=owner, tokenUrl=tokenUrl, tokenMeta = tokenMeta)

def set_nft_operator(user:Person, operator:str, allowed:bool=True, gas_price:int=None, erc721_address:str=None):
    with app.open_resource('misc/ERC721.abi',mode='rt') as f:
        abi = f.read().replace('\n','').replace('\r','')
        web3_rpc_endpoint = oas_config.get('WEB3_RPC_URL')
        w3 = Web3(Web3.HTTPProvider(web3_rpc_endpoint, request_kwargs={'timeout': 60}))
        chainId = w3.eth.chain_id
        erc721_address = erc721_address or Web3.toChecksumAddress(oas_config.get('NFT_TOKEN_ADDRESS'))  
        nft = w3.eth.contract(address=erc721_address, abi=abi)
        person_id = user.person_id
        wallet_address, d_path, private_key = new_oas_address(str(person_id), use_ex_priv=True)
        nonce = w3.eth.getTransactionCount(wallet_address) 
        action = nft.functions.setApprovalForAll(Web3.toChecksumAddress(operator), allowed)
        estimatedGas = action.estimateGas({'from': wallet_address, 'value': 0})
        gas = estimatedGas + 50000
        currentGasPrice = w3.eth.gas_price
        gasPrice = w3.toWei(gas_price, 'gwei') if gas_price else currentGasPrice + w3.toWei(1, 'gwei')
        txn = action.buildTransaction({'chainId':chainId, 'gas': gas, 'gasPrice': gasPrice, 'nonce': nonce})
        signed_txn = w3.eth.account.signTransaction(txn, private_key=private_key)
        tx_hash = signed_txn.hash.hex()
        w3.eth.sendRawTransaction(signed_txn.rawTransaction) 
        return tx_hash

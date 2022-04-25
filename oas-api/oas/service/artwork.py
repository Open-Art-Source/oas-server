from flask import current_app as app, g
from io import BytesIO
import uuid
import hashlib
from datetime import datetime
from typing import Any, Dict, List, Union, NoReturn, Optional
from sqlalchemy import or_, and_
from oas.model.artist import Artist
from oas.model.artwork import Artwork
from oas.model.non_fungible_token import NftToken
from oas.model.ownership import Ownership
from oas.model.person import Person
from oas.model.listing import Listing
from oas.model.listing_price import ListingPrice
from oas.model.purchase import Purchase
from oas.service.hdwallet import MINTER_WALLET
from oas.service.hdwallet import new_oas_address, new_hdwallet, make_subwallet
from web3 import Web3
from web3._utils.filters import construct_event_filter_params
from web3._utils.events import get_event_data
from web3.datastructures import AttributeDict
from web3.exceptions import BlockNotFound
from eth_abi.codec import ABICodec
from oas.exception import NotOwnerException
from oas.service.stacks import get_balances, get_transaction
from oas.service.storage import cloud_save, FileObject
from oas.service.artist import collect_nft_token

import oas.config as oas_config
import simplejson as json
import requests

def list_artwork(filter: dict, commit: Optional[bool]=True) -> Any:
    artwork_id = filter.get('artwork_id')
    person_id = filter.get('person_id') 
    listing_id = filter.get('listing_id')
    price_id = filter.get('price_id')
    currency = filter.get('currency')
    amount = filter.get('amount') 
    re_submit = filter.get('re_submit')
    booster = filter.get('booster')
    was_active = None
    old_amount = None
    checking = filter.get('check')
    active = filter.get('active') if not checking else None
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
        if (active or checking) and not token_id: raise Exception('nft token is still minting')


    owner = [ o for o in (artworks[0].ownership or [] if artworks else []) if not o.end_date and o.person_id == person_id ]
    if not owner:
        raise NotOwnerException('not owner')
    
    listing = [ l for l in (owner[0].listing or [] if owner else []) ]
    currency = 'STX' if not currency else currency
    purchase = None
    listing_price = [ p for p in (listing[0].listing_price or [] if listing else []) if p.price_id == price_id or p.currency == currency ]
    if not listing:
        listing = Listing.from_dict(dict(ownership_id = owner[0].ownership_id, artwork_id = artwork_id, person_id = person_id, active = active ))
        if not checking: session.add(listing)
        else: raise Exception("not listed")
    else:
        listing = listing[0]
        was_active = listing.active
        purchase = listing.purchase and listing.purchase[0] and listing.purchase[0].status not in [3,7]
        if not purchase and not checking:
            listing.active = active if active is not None else listing.active
            listing.status = 0
    
    if listing_price:
        old_amount = listing_price[0].amount
        if not purchase and not checking:
            listing_price[0].amount = amount if amount != None else old_amount
        amount = listing_price[0].amount        
    elif currency and amount:
        item_price = ListingPrice.from_dict(dict(listing_id = listing.listing_id, currency = currency, amount = amount))
        listing.listing_price.append(item_price)
        listing_price = [ p for p in (listing.listing_price or [] if listing else []) if p.currency == currency ]
    
    if not listing_price and checking: raise Exception("not listed")

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
                    old_status = listing_price[0].status 
                elif tx_status != 'pending':
                    listing_price[0].status = 3 if old_status == 1 else 6
                    old_status = listing_price[0].status 
                else:
                    #listing.status = False
                    pass
            elif error:
                if '404' in error['message']:
                    #listing_price[0].status = 0
                    pass

        if not checking and (active == True and (not purchase) and ((not was_active or float(old_amount) != float(amount) or old_status in [0, 3, 6] or (old_status == 1 and re_submit)))):
            if not amount or amount < 0: raise Exception('price must be set and > 0')
            stx_amount = amount * 1000000
            json_rpc = {
                'id': '1',
                'jsonrpc': "2.0",
                'method': "list_nft_token",
                'params': [stx_address, stx_token_id, stx_amount, stx_secret, stx_password, dict(booster= booster if booster else (2 if re_submit else 1))]
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
        elif not checking and active == False and (not purchase) and (was_active or old_status in [2] or (old_status == 4 and re_submit)):
            if old_status == 2:
                json_rpc = {
                    'id': '1',
                    'jsonrpc': "2.0",
                    'method': "delist_nft_token",
                    'params': [stx_address, stx_token_id, stx_secret, stx_password, dict(booster=booster or 4 if re_submit else 1)]
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

    if purchase and not checking:
        raise Exception('someone purchase this, cannot change listing state')

    return listing, listing_price


def get_listing(filter: dict = dict()) -> Any:
    _filter = filter or dict()
    active = _filter.get('active')
    person_id = _filter.get('person_id')
    artist_id = _filter.get('artist_id')
    currency = _filter.get('currency')
    session = app.db_session
    listing = session.query(Listing).join(Listing.artwork).join(Listing.listing_price).filter(
                                                and_(Listing.active == (active if active is not None else True)
                                                 , or_(Listing.person_id == person_id, not person_id
                                                       )
                                                 , or_(and_(ListingPrice.currency == currency
                                                          , or_( ListingPrice.status == 1 , ListingPrice.status == 2)), not currency)
                                                 )).filter(or_(Artwork.artist_id == artist_id, not artist_id)).filter(Listing.listing_price)

    return listing

def purchase(filter: dict = dict(), commit: Optional[bool]=True) -> Any:
    _filter = filter or dict()
    active = True
    artwork_id = _filter.get('artwork_id')
    currency = _filter.get('currency')
    re_submit = _filter.get('re_submit')
    checking = _filter.get('check')
    cancel = _filter.get('cancel')
    booster = _filter.get('booster')
    session = app.db_session
    user = g.user
    order = None
    listings = session.query(Listing).join(Listing.artwork).outerjoin(Listing.purchase).filter(
                                                and_(
                                                     Listing.active == True
                                                     , Listing.artwork_id == artwork_id
                                                     , or_(
                                                        Listing.status == 0
                                                        , Listing.status == None
                                                        , Purchase.buyer_id == user.person_id
                                                        )
                                                     , Listing.person_id != user.person_id
                                                    ))
    listing = listings.first()
    if listing:
        listing_price = [ x for x in listing.listing_price if x.currency == currency and x.tx_hash and x.status in [ 1, 2] ]
        purchase = [ p for p in listing.purchase if not p.completed_on ]
        tx_info = None
        tx_hash = None
        purchase_status = 0
        if listing_price and currency == 'STX' and listing_price[0].tx_hash and listing_price[0].status == 1:
            tx_result = get_transaction(listing_price[0].tx_hash)
            result = tx_result.get('result')
            error = tx_result.get('error')
            if result:
                tx_status = result['tx_status']
                if tx_status == 'success':
                    listing_price[0].status = 2 if listing_price[0].status == 1 else 5
                elif tx_status != 'pending':
                    listing_price[0].status = 3 if listing_price[0].status == 1 else 6
                else:
                    #listing.status = False
                    pass
            elif error:
                if '404' in error['message']:
                    #listing_price[0].status = 0
                    pass

        if purchase and purchase[0].tx_hash:
            oas_stacks_api_endpoint = oas_config.get('OAS_STACKS_RPC_URL')
            tx_hash = purchase[0].tx_hash
            purchase_status = purchase[0].status
            if purchase_status < 2:
                json_rpc = {
                    'id': '1',
                    'jsonrpc': "2.0",
                    'method': "get_transaction",
                    'params': [purchase[0].tx_hash]
                    }
                payload = json.dumps(json_rpc)
                response = requests.post(oas_stacks_api_endpoint, json=json_rpc)
                result = response.json()
                tx_info = result.get('result')
                if tx_info:
                    tx_status = tx_info['tx_status']
                    if tx_status == 'success': 
                        purchase[0].status = 2
                        purchase_status = 2
                    elif tx_status != 'pending': 
                        purchase[0].status = 3
                        purchase_status = 3

        if not checking and listing_price and listing_price[0].status == 2 and  currency == 'STX' and (not tx_hash or (re_submit and purchase_status in [0, 1, 3])):
            stx_token_id = listing.artwork.stx_token_id
            person_id = user.person_id
            stx_secret = user.stx_secret
            ownership = listing.ownership
            owner = ownership.person.stx_address if ownership else None

            wallet_address, d_path, private_key = new_oas_address(str(person_id), use_ex_priv=True)
            oas_stacks_api_endpoint = oas_config.get('OAS_STACKS_RPC_URL')
            sip009_address = oas_config.get('OAS_STACKS_NFT_CONTRACT')
            stx_amount = listing_price[0].amount * 1000000
            stx_password = hashlib.sha256(private_key.encode('utf-8')).hexdigest()
            json_rpc = {
                'id': '1',
                'jsonrpc': "2.0",
                'method': "purchase_nft_token",
                'params': [owner, stx_token_id, stx_amount, stx_secret, stx_password, dict(booster= booster or (4 if re_submit else 1))]
                }
            payload = json.dumps(json_rpc)
            response = requests.post(oas_stacks_api_endpoint, json=json_rpc)
            result = response.json()
            tx_result = result.get('result')
            if tx_result:
                tx_hash = '0x' + tx_result['txid']
                listing.status = 1
                if purchase:
                    purchase[0].tx_hash = tx_hash
                    purchase[0].status = 1
            else: raise Exception(result)

        if tx_hash and not purchase:
            order = Purchase(buyer_id=user.person_id
                             , seller_id = listing.person_id
                             , listing_id = listing.listing_id
                             , status = 1
                             , currency = currency, tx_hash = tx_hash) 
            session.add(order)
        elif tx_hash:
            order = purchase[0]

        if cancel and purchase and purchase[0].status == 3:
            purchase[0].status = 7
            purchase[0].completed_on = datetime.now()
            listing.status = 0

        if commit: session.commit()
        return order

def confirm_purchase(filter: dict = dict(), commit: Optional[bool]=True) -> Any:
    _filter = filter or dict()
    artwork_id = _filter.get('artwork_id')
    re_submit = _filter.get('re_submit')
    checking = _filter.get('check')
    booster = _filter.get('booster')
    session = app.db_session
    user = g.user

    purchases = session.query(Purchase).join(Purchase.listing).filter(
                                                and_(
                                                    Listing.artwork_id == artwork_id
                                                    ,or_(
                                                    and_(Purchase.buyer_id == user.person_id)
                                                    )
                                                    ,Purchase.status < 5
                                                    )).filter(Listing.artwork_id == artwork_id)
    x = [ p for p in purchases ]
    purchase =  purchases.first()
    if purchase:
        currency = purchase.currency
        listing = purchase.listing
        ownership = listing.ownership
        artwork = listing.artwork
        listing_price = [ p for p in listing.listing_price if p.currency == currency ]
        confirm_tx_hash = purchase.confirm_tx_hash
        tx_hash = purchase.tx_hash
        old_status = purchase.status

        if old_status in [0, 1]:
            tx_result = get_transaction(tx_hash)
            result = tx_result.get('result')
            error = tx_result.get('error')
            if result:
                tx_status = result['tx_status']
                if tx_status == 'success':
                    purchase.status = 2 
                    old_status = 2
                elif tx_status != 'pending':
                    purchase.status = 3 
                    old_status = 3
                else:
                    #listing.status = False
                    pass
            elif error:
                if '404' in error['message']:
                    purchase.status = 0
                    old_status = 0

        if old_status == 4 and confirm_tx_hash:
            oas_stacks_api_endpoint = oas_config.get('OAS_STACKS_RPC_URL')
            json_rpc = {
                'id': '1',
                'jsonrpc': "2.0",
                'method': "get_transaction",
                'params': [confirm_tx_hash]
                }
            payload = json.dumps(json_rpc)
            response = requests.post(oas_stacks_api_endpoint, json=json_rpc)
            result = response.json()
            tx_info = result.get('result')
            if tx_info:
                tx_status = tx_info['tx_status']
                if tx_status == 'success': 
                    purchase.status = 5
                    listing.status = 2
                    re_submit = False
                    ownership.end_date = datetime.now()
                    new_owner = Ownership.from_dict(dict(person=user, artwork=artwork))
                    session.add(new_owner)
                    purchase.completed_on = datetime.now()

                elif tx_status == 'failed': purchase.status = 6
               
        if not checking and (old_status == 2 or (re_submit and (old_status == 4 or old_status == 6))) and currency == 'STX' and (not confirm_tx_hash or re_submit):
            stx_token_id = listing.artwork.stx_token_id
            person_id = user.person_id
            stx_secret = user.stx_secret
            owner = ownership.person.stx_address if ownership else None
            wallet_address, d_path, private_key = new_oas_address(str(person_id), use_ex_priv=True)
            oas_stacks_api_endpoint = oas_config.get('OAS_STACKS_RPC_URL')
            sip009_address = oas_config.get('OAS_STACKS_NFT_CONTRACT')
            stx_amount = listing_price[0].amount * 1000000
            stx_password = hashlib.sha256(private_key.encode('utf-8')).hexdigest()
            json_rpc = {
                'id': '1',
                'jsonrpc': "2.0",
                'method': "confirm_nft_token",
                'params': [owner, stx_token_id, stx_amount, stx_secret, stx_password, dict(booster=booster or (4 if re_submit else 1))]
                }
            payload = json.dumps(json_rpc)
            response = requests.post(oas_stacks_api_endpoint, json=json_rpc)
            result = response.json()
            tx_result = result.get('result')
            if tx_result:
                tx_hash = '0x' + tx_result['txid']
                purchase.confirm_tx_hash = tx_hash
                purchase.status = 4
                purchase.listing.status = 4
            else: raise Exception(result)

        if commit: session.commit()
        return purchase

def get_purchases(filter: dict = dict()) -> Any:
    _filter = filter or dict()
    session = app.db_session
    user = g.user
    as_seller = _filter.get('as_seller') 
    as_buyer = not as_seller 
    purchases = session.query(Purchase).join(Listing.artwork).filter(
                                                and_(
                                                    or_(
                                                    and_(Purchase.buyer_id == user.person_id, as_buyer),
                                                    and_(Purchase.seller_id == user.person_id, not as_buyer)
                                                    )
                                                    ))
    for p in purchases:
        tx_hash = p.tx_hash
        status = p.status
        currency = p.currency
        if tx_hash and (status == 1 or status == 3):
            if currency == 'STX':
                tx = get_transaction(tx_hash)

    return purchases


def make_nft_tokenUri(filter: dict, commit: Optional[bool]=True) -> Any:
    session = app.db_session
    artwork_id = filter.get('artwork_id')
    owner = filter.get('person_id')
    artworks = session.query(Artwork).filter(and_(Artwork.artwork_id == artwork_id))
    old_artwork = artworks.first()
    if old_artwork:
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
        
        return token_uri


def register_nft_token(filter: dict, commit: Optional[bool]=True) -> Any:
    erc721_address = Web3.toChecksumAddress(oas_config.get('NFT_TOKEN_ADDRESS'))  
    artwork_id = filter.get('artwork_id')
    person_id = filter.get('person_id') 
    tx_hash = filter.get('tx_hash')
    contract_address = filter.get('erc721_address') or erc721_address

    session = app.db_session
    artwork = [ a for a in session.query(Artwork).filter(and_(Artwork.artwork_id == artwork_id)) ]
    owner = [ o for o in (artwork[0].ownership or [] if artwork else []) if not o.end_date and o.person_id == person_id ]
    if not owner:
        raise NotOwnerException('not owner')

    old_artwork = artwork[0]

    if old_artwork:
        old_token = [ t for t in old_artwork.non_fungible_token if t.tx_hash == tx_hash and t.contract_address == contract_address ]
        token_id = None
        token = None
        if not old_token:
            nft_token = NftToken.from_dict(dict(contract_address = contract_address, artwork_id = artwork_id, tx_hash = tx_hash))
            old_artwork.non_fungible_token.append(nft_token)
            if commit: session.commit()
        try:
            token = collect_nft_token(filter, commit)
        except:
            pass

        return dict(contract_address = contract_address, token_id = token['token_id'] if token else None, tx_hash = tx_hash)

from io import BytesIO
from flask import current_app as app, g
from flask_jsonrpc import JSONRPCBlueprint
from typing import Any, Dict, List, Union, NoReturn, Optional
from numbers import Real
from oas.api import AuthorizationView
from oas.model.artwork import Artwork
from oas.service.hdwallet import new_oas_address, new_hdwallet, make_subwallet
from oas.service.artist import register_artwork, get_artwork, delete_artwork, make_nft_token, nft_token_info
from oas.service.artist import collect_nft_token, transfer_nft_token, get_nft_token, set_nft_operator, raw_transfer_nft_token
from oas.service.storage import cloud_save, FileObject
from oas.service.artwork import make_nft_tokenUri, register_nft_token, purchase, get_purchases, confirm_purchase, list_artwork, get_listing
from oas.service.aimodel import compare_ipfs_content
from oas.helper import get_firebase_claim, get_credential
from web3 import Web3
#import json
import simplejson as json
import ipfshttpclient
import re
import os
import requests
import oas.config as oas_config

artwork = JSONRPCBlueprint('artwork', __name__, jsonrpc_site_api=AuthorizationView)

@artwork.method('offchain_id')
def offchain_id(artwork_id:str) -> Any:
    return Web3.keccak(text=artwork_id).hex()

@artwork.method('list_for_sale')
def add_listing(artwork_id:str, currency:str, options: dict = dict()) -> Any:
    user = g.user
    listing, listing_price = list_artwork(dict(person_id = user.person_id
                      , artwork_id = artwork_id 
                      , currency = currency 
                      , active = options.get('active') if options.get('active') != None else True
                      , amount = options.get('amount')
                      , re_submit = options.get('re_submit')
                      , booster = options.get('booster')
                      ))

    x = listing.to_dict()
    x['listing_price'] = [y.to_dict() for y in listing.listing_price]
    return x

@artwork.method('check_listing')
def check_listing(artwork_id:str, currency:str, options: dict = dict()) -> Any:
    user = g.user
    listing, listing_price = list_artwork(dict(person_id = user.person_id
                      , artwork_id = artwork_id 
                      , currency = currency
                      , check = True
                      ))

    x = listing.to_dict()
    x['listing_price'] = [y.to_dict() for y in listing.listing_price]
    return x

@artwork.method('get_holdings')
def get_artwork(filter: dict = dict()) -> Any:
    artist_id = filter.get('artist_id')
    listed = filter.get('listed')
    session = app.db_session
    user = g.user
    artworks = session.query(Artwork).join(Artwork.listing).join(Artwork.ownership).filter(
                                    and_(
                                        Ownership.person_id == user.person_id
                                        ,Ownership.end_date == None
                                        ,or_(Listing.active == listed, listed == None)
                                        )
                                    )
    x = [ a.to_dict() for a in  artworks ]
    return x

@artwork.method('get_listing')
def listing(filter: dict = None) -> Any:
    def expand_listing(l) -> Any:
        _l = l.to_dict()
        _l['artwork'] = l.artwork.to_dict()
        _l['owner'] = l.person.to_dict()
        _l['artist'] = l.artwork.artist.to_dict()
        _l['price'] = [ p.to_dict() for p in l.listing_price]
        return _l
    user = g.user
    person_id = user.person_id
    listing = get_listing(filter)
    return [ expand_listing(l) for l in listing ]

@artwork.method('purchase')
def purchase_artwork(artwork_id:str, currency:str, options: dict() = dict()) -> Any:
    po = purchase(dict(artwork_id = artwork_id, currency = currency, re_submit = options.get('re_submit'), booster = options.get('booster')))
    if po:
        return po.to_dict()
    else:
        raise Exception("artwork not available")

@artwork.method('check_purchase')
def check_purchase(artwork_id:str, currency:str, options: dict = dict()) -> Any:
    po = purchase(dict(artwork_id = artwork_id, currency = currency, check = True))
    if po:
        return po.to_dict()
    else:
        raise Exception("artwork not available")

@artwork.method('cancel_purchase')
def cancel_purchase(artwork_id:str, currency:str, options: dict() = dict()) -> Any:
    po = purchase(dict(artwork_id = artwork_id, currency = currency, check = True, cancel = True))
    if po:
        return po.to_dict()
    else:
        raise Exception("artwork not available")

@artwork.method('confirm_purchase')
def confirm_artwork_purchase(artwork_id:str, options: dict = dict()) -> Any:
    po = confirm_purchase(dict(artwork_id = artwork_id, re_submit = options.get('re_submit'), booster = options.get('booster')))
    if po:
        return po.to_dict()
    else:
        raise Exception("no purchase record")

@artwork.method('check_confirm_purchase')
def check_confirm_purchase(artwork_id:str, options:dict = dict()) -> Any:
    po = confirm_purchase(dict(artwork_id = artwork_id, check = True))
    if po:
        return po.to_dict()
    else:
        raise Exception("no purchase record")

@artwork.method('get_purchases')
def purchase_list(filter:dict = dict()) -> Any:
    def get_price(l, currency):
        listing = l.to_dict()
        listing_price = [ o.to_dict() for o in (l.listing_price or []) if o.currency == currency]
        return listing_price[0]['amount'] if listing_price else None

    def get_tree(purchase):
        p = purchase.to_dict()
        listing = purchase.listing
        seller = purchase.seller
        buyer = purchase.buyer
        currency = purchase.currency
        p['listing_price'] = get_price(listing, currency)
        p['artwork'] = listing.artwork.to_dict()
        return p

    plist = get_purchases(filter)
    y = map(get_tree, plist)
    return [x for x in y ]

@artwork.method('compare_ipfs')
def compare_ipfs(item1_hash:str, item2_hash:str, filename1:str=None, filename2:str=None) -> Any:
    #ipfs_client = ipfshttpclient.connect(oas_config.get('IPFS_API_URL'),auth=get_credential(oas_config.get('IPFS_API_CREDENTIAL')))
    #dir = ipfs_client.ls(item1_hash).as_json()
    #object_hash = dir['Objects'][0]['Hash']
    #sub_items = dir['Objects'][0]['Links']
    ipfs_base_url = oas_config.get('IPFS_BASE_URL')
    #x = sub_items[0]
    item1_url = f"{ipfs_base_url}/{item1_hash}/{str(filename1 or '')}"
    item2_url = f"{ipfs_base_url}/{item2_hash}/{str(filename2 or '')}"
    return compare_ipfs_content(item1_url, item2_url)
from base64 import b64decode, b64encode
from io import BytesIO
from flask import current_app as app, g
from flask_jsonrpc import JSONRPCBlueprint
from typing import Any, Dict, List, Union, NoReturn, Optional
from datetime import datetime
from numbers import Real
from oas.api import AuthorizationView
from oas.model.artwork import Artwork
from oas.service.hdwallet import new_oas_address, new_hdwallet, make_subwallet
from oas.service.artist import register_artwork, get_artwork, delete_artwork, make_nft_token, nft_token_info
from oas.service.artist import collect_nft_token, transfer_nft_token, get_nft_token, set_nft_operator, raw_transfer_nft_token
from oas.service.storage import cloud_save, FileObject
from oas.service.artwork import make_nft_tokenUri, register_nft_token, list_artwork
from oas.service.user import register, load_user_context

#import json
import simplejson as json
import re
import os
import requests
import oas.config as oas_config

artist = JSONRPCBlueprint('artist', __name__, jsonrpc_site_api=AuthorizationView)

@artist.method('register_artwork')
def reg_artwork(artwork: dict, files: Optional[List[Dict]]=None) -> Any:
    cloud_file = []
    dirname = ''
    user = g.user
    artist = user.artist
    artwork_info = dict(artwork_id = artwork.get('artwork_id'),
                        title=artwork.get('title'),
                        medium=artwork.get('medium'),
                        length=artwork.get('length'),
                        width=artwork.get('width'),
                        height=artwork.get('height'),
                        description=artwork.get('description'),
                        short_description=artwork.get('short_description'),
                        dimension_unit=artwork.get('dimension_unit'),
                        primary_image_file_name=artwork.get('primary_image_file_name'),
                        date_created = datetime.strptime(artwork.get('date_created'),'%a, %d %b %Y %H:%M:%S %Z') if artwork.get('date_created') else None
                        )
    _artwork = Artwork.from_dict(artwork_info)
    _artwork = register_artwork(artist, _artwork)

    if files:
        metadata = dict(artwork_id = _artwork.artwork_id,
            title = _artwork.title,
            description = _artwork.description,
            icon = "filename")
        
        cloud_file = cloud_save([ FileObject(file = BytesIO(b64decode(f.get('base64'))), filename=f.get('filename')) for f in files] + [FileObject(file = BytesIO(bytes(json.dumps(metadata),'utf8')), filename='metadata.json')])
        folder = cloud_file[-1]
        dirname = os.path.split(folder['Name'] if folder else '')[-1]
        if folder:
            hash = folder["Hash"]
            _artwork.image_files_hash = hash
            register_artwork(artist, _artwork)

    listing = artwork.get("listing")
    if listing:
        list_artwork(dict(artwork_id = _artwork.artwork_id,
                        person_id = user.person_id,
                        active = listing.get('active') if listing.get('active') is not None else None,
                        currency = listing.get('currency'),
                        amount = listing.get('amount'),
                        ))

    return { 
        "artwork_id" : _artwork.artwork_id,
        "ipfs": [dict(Name=re.sub('^' + dirname + '/?','', x["Name"]), Hash=x["Hash"], Size=x["Size"]) for x in cloud_file]
    }

@artist.method('get_artwork')
def artworks(filter: Optional[dict]=None) -> List[dict]:
    def get_ownership(artwork):
        a = artwork.to_dict()
        a['ownership'] = [ o.to_dict() for o in (artwork.ownership or [])]
        return a
    def get_listing(l):
        listing = l.to_dict()
        listing['listing_price'] = [ o.to_dict() for o in (l.listing_price or [])]
        return listing

    def get_tree(artwork):
        a = artwork.to_dict()
        a['ownership'] = [ o.to_dict() for o in (artwork.ownership or [])]
        a['listing'] = [ get_listing(o) for o in (artwork.listing or [])]
        return a

    user = g.user
    person_id = user.person_id if user else None
    artist = user.artist if user else None
    _filter = dict(artist_id=artist.artist_id if artist else None) if not filter else filter.copy()
    if _filter.get('owned'): _filter['person_id'] = person_id
    _artworks = get_artwork(_filter)
    #z = map(get_ownership, _artworks)
    z = map(get_tree, _artworks)
    #x = [a.to_dict() for a in _artworks]
    x = [o for o in z]
    return x
    for y in x:
        y["length"] = float(str(y["length"])) if y["length"] else None
        y["width"] = float(str(y["width"])) if y["width"] else None
        y["height"] = float(str(y["height"])) if y["height"] else None
    return x

@artist.method('delete_artwork')
def del_artwork(filter: dict) -> Any:
    user = g.user
    artist = user.artist if user else None
    _filter = dict(artist_id=artist.artist_id, artwork_id = filter.get('artwork_id'))
    return delete_artwork(_filter)

@artist.method('make_nft_token_uri')
def make_token_uri(artwork_id: str) -> Any:
    user = g.user
    person_id = user.person_id
    artist = user.artist if user else None
    if person_id:
        _filter = dict(artist_id=artist.artist_id, artwork_id = artwork_id)
        tokenUri = make_nft_tokenUri(_filter)
        return tokenUri if tokenUri else {'message': 'failed to create token uri'}
    return {'message': 'nothing to create'}

@artist.method('register_nft_token')
def register_token(filter: dict) -> Any:
    user = g.user
    person_id = user.person_id
    artist = user.artist if user else None
    if person_id:
        _filter = dict(artwork_id = filter.get('artwork_id'), tx_hash = filter.get('tx_hash'), person_id = person_id)
        token = register_nft_token(_filter)
        return token if token else {'message': 'nothing to register'}
    return {'message': 'nothing to register'}

@artist.method('make_nft')
def make_nft(artwork_id: str, options: dict = dict(token = 'STX')) -> Any:
    user = g.user
    person_id = user.person_id
    artist = user.artist if user else None
    if person_id:
        wallet_address, d_path, private_key = new_oas_address(str(person_id), use_ex_priv=False)
        _filter = dict(artist_id=artist.artist_id
                       , artwork_id = artwork_id
                       , owner_wallet_address = wallet_address
                       , re_mint= options.get('re_submit')
                       , booster = options.get('booster')
                       , token = options.get('token'))
        token = make_nft_token(_filter)
        return token if token else {'message': 'nothing to mint'}
    return {'message': 'nothing to mint'}

@artist.method('collect_nft')
def collect_nft(artwork_id: str) -> Any:
    user = g.user
    artist = user.artist if user else None
    _filter = dict(artist_id=artist.artist_id, artwork_id = artwork_id)
    token = collect_nft_token(_filter)
    if not token: raise Exception('not minted')
    return token

@artist.method('transfer_nft')
def transfer_nft(artwork_id: str, token_id:str, to:str, gas_price:int=None) -> Any:
    user = g.user
    artist = user.artist if user else None
    _filter = dict(artist_id=artist.artist_id, artwork_id = artwork_id)
    txn = transfer_nft_token(user, to, token_id, _filter, gas_price)
    return {'tx_hash': txn}

@artist.method('raw_transfer_nft')
def raw_transfer_nft(token_id:str, to:str, erc721_address:str=None) -> Any:
    user = g.user
    artist = user.artist if user else None
    txn = raw_transfer_nft_token(user, to, token_id, erc721_address=erc721_address)
    return {'tx_hash': txn}

@artist.method('approve_operator')
def approve_operator(operator: str, allowed:bool=True, erc721_address:str=None) -> Any:
    user = g.user
    txn = set_nft_operator(user, operator, allowed, erc721_address=erc721_address)
    return {'tx_hash': txn}

@artist.method('nft_owner')
def get_nft_owner(artwork_id: str, token_id:str=None) -> Any:
    user = g.user
    artist = user.artist if user else None
    _filter = dict(artist_id=artist.artist_id, artwork_id = artwork_id)
    token = get_nft_token(_filter, token_id)
    return token

@artist.method('raw_nft_info')
def get_nft_token(token_id:str, erc721_address:str=None) -> Any:
    token = nft_token_info(token_id, erc721_address=erc721_address)
    return token

@artist.method('certify_image')
def certify_image() -> Any:
    instance_path = app.instance_path
    root_path = app.root_path
    filename1 = os.path.join(app.root_path, 'misc', 'kitten_small.jpg')
    filename2 = os.path.join(app.root_path, 'misc', 'kitten_small_01.jpg')
    files = {
        'image-0': open(filename1, 'rb'),
        'image-1': open(filename1, 'rb'),
        }
    pytorch_endpoint = oas_config.get('PYTORCH_URL')
    pytorch_model_endpoint = f'{pytorch_endpoint}/image_dissimilarity'
    r = requests.post(pytorch_model_endpoint, files = files)
    result = r.json()
    return dict(prediction = result, file = 'kitten_small.jpg')

@artist.method('identify_image')
def certify_image() -> Any:
    instance_path = app.instance_path
    root_path = app.root_path
    pytorch_endpoint = oas_config.get('PYTORCH_URL')
    filename = os.path.join(app.root_path, 'misc', 'kitten_small.jpg')
    pytorch_model_endpoint = f'{pytorch_endpoint}/densenet161'
    with open(filename, 'rb') as f:
        x = f.read()
        r = requests.put(pytorch_model_endpoint, data = x)
        result = r.json()
        return dict(prediction = result, file = 'kitten_small.jpg')
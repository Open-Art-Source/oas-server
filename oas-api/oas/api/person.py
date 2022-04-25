import uuid
import os
from flask import current_app as app, g
from flask_jsonrpc import JSONRPCBlueprint
from typing import Any, Dict, List, Union, NoReturn, Optional, Tuple
from sqlalchemy import or_, and_
from numbers import Real
from oas.api import AuthorizationView
from oas.model.database import SessionLocal
from oas.model.artist import Artist
from oas.model.artwork import Artwork
from oas.model.non_fungible_token import NftToken
from oas.model.ownership import Ownership
from oas.model.listing import Listing
from oas.model.listing_price import ListingPrice
from oas.model.purchase import Purchase
from oas.model.person import Person
from oas.service.hdwallet import new_oas_address, new_hdwallet, make_subwallet, MINTER_WALLET
from oas.service.user import deploy_erc721, send_eth, send_erc20, deploy_erc1967Proxy, erc721_check, create_stx_wallet, deploy_chainlinkToken
from oas.service.chainlink import deploy_operatorFactory
from oas.service.artwork import get_listing, list_artwork
from oas.service.stacks import get_balances
from datetime import datetime
from oas.api import UnauthorizedError

person = JSONRPCBlueprint('person', __name__, jsonrpc_site_api=AuthorizationView)

admin = ["af80f8a8-73a3-42a7-979c-dd07e508bf42","8a8c3534-1c28-4077-94c3-2fd33786c2da","fdc26d2a-7937-44e2-9094-e7929d206385"]

@person.method('index')
def index(filter: Optional[dict]=None, count: Optional[int]=None) -> Any:
    session = app.db_session
    users = session.query(Person)
    x = [
        {"first_name": u.first_name, "wallet_address": u.custodian_wallet_address, "stx_wallet_addess": u.stx_address} for u in users.all()
        ]
    return x
    #return type('',(dict,),{'name':'woody', 'age':'25'})()
    #return [1,"abc"]
@person.method('add')
def add(first_name: str, last_name: str, authToken: str, commit: Optional[bool]=True) -> Any:
    user = Person(first_name=first_name, last_name = last_name, date_time_joined = datetime.now(), person_id = uuid.uuid4())
    session = app.db_session
    session.add(user)
    if commit: session.commit()
    return { "person_id" : user.person_id}

@person.method('list_for_sale')
def add_listing(listing: dict) -> Any:
    user = g.user
    listing, listing_price = list_artwork(dict(person_id = user.person_id
                      , active = listing.get('active')
                      , artwork_id = listing.get('artwork_id') 
                      , currency = listing.get('currency') 
                      , amount = listing.get('amount')))

    x = listing.to_dict()
    x['listing_price'] = [y.to_dict() for y in listing.listing_price]
    return x

@person.method('get_holdings')
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

@person.method('wallet')
def wallet(person_id:str=None) -> Any:
    user = g.user
    if (not user.person_id in admin) or not person_id:
        person_id = user.person_id
    wallet_address, d_path, private_key = new_oas_address(str(person_id), use_ex_priv=True)
    stx_wallet = create_stx_wallet(private_key)
    return { "address" : wallet_address
            , "stx_address": stx_wallet['stx_address']
            #, "private_key": private_key
            }

@person.method('stx_wallet')
def get_stx_wallet(person_id:str=None) -> Any:
    user = g.user
    if (not user.person_id in admin) or not person_id:
        person_id = user.person_id
    if not user.stx_secret:
      wallet_address, d_path, private_key = new_oas_address(str(person_id), use_ex_priv=True)
      stx_wallet = create_stx_wallet(private_key)
      session = app.db_session

    return { "address" : wallet_address, "private_key": private_key}

@person.method('get_balance')
def get_balance(filter: dict = dict()) -> Any:
    token = filter.get('token') or 'STX'
    session = app.db_session
    user = g.user
    _wallet = wallet(user.person_id)
    balance = get_balances(_wallet['stx_address'])
    result = balance.get('result')
    error = balance.get('error')
    if result:
        return dict(stx_address=_wallet['stx_address'], balances = result)
    else:
        return dict(stx_address=_wallet['stx_address'], error = error)

@person.method('minter_address')
def minter_wallet(person_id:str=None) -> Any:
    user = g.user
    if (not user.person_id in admin) or not person_id:
        person_id = user.person_id
    wallet_address, d_path, private_key = MINTER_WALLET
    return { "address" : wallet_address}

@person.method('new_hdwallet')
def hdwallet() -> Any:
    user = g.user
    person_id = user.person_id
    wallet = new_hdwallet()
    ex_pub = wallet['ex_pub']
    ex_priv = wallet['ex_priv']
    address, path, private_key = make_subwallet([0,0], ex_pub, ex_priv)
    assert(wallet['priv'] == private_key)
    return wallet

@person.method('deploy_erc721')
def erc721(gas_price:int=None) -> Any:
    user = g.user
    person_id = user.person_id
    if person_id in admin:
       tx_hash = deploy_erc721(gas_price)
       return {"tx_hash" : tx_hash}
    else:
        raise UnauthorizedError("not authorized to do this")

@person.method('deploy_chainlinkToken')
def chainlinkToken(gas_price:int=None) -> Any:
    user = g.user
    person_id = user.person_id
    if person_id in admin:
       tx_hash = deploy_chainlinkToken(gas_price)
       return {"tx_hash" : tx_hash}
    else:
        raise UnauthorizedError("not authorized to do this")

@person.method('deploy_chainlinkOperatorFactory')
def chainlinkOperatorFactory(link_token_address:str=None, gas_price:int=None) -> Any:
    user = g.user
    person_id = user.person_id
    if person_id in admin:
       tx_hash = deploy_operatorFactory(link_token_address, gas_price)
       return {"tx_hash" : tx_hash}
    else:
        raise UnauthorizedError("not authorized to do this")

@person.method('deploy_erc1967')
def erc1967(gas_price:int=None) -> Any:
    user = g.user
    person_id = user.person_id
    if person_id in admin:
       tx_hash = deploy_erc1967Proxy(gas_price)
       return {"tx_hash" : tx_hash}
    else:
        raise UnauthorizedError("not authorized to do this")

@person.method('erc721_check')
def erc1967_check(gas_price:int=None) -> Any:
    user = g.user
    person_id = user.person_id
    return erc721_check()

@person.method('send_eth')
def send_ETH(to:str, eth:float, gas_price:int=None) -> Any:
    user = g.user
    person_id = user.person_id
    if person_id in admin:
       tx_hash = send_eth(to, eth, gas_price)
       return {"tx_hash" : tx_hash}
    else:
        raise UnauthorizedError("not authorized to do this")

@person.method('send_erc20')
def send_ERC20(to:str, amount:float, token_address:str = None,  decimal:int=18, gas_price:int=None) -> Any:
    user = g.user
    person_id = user.person_id
    if person_id in admin:
       tx_hash = send_erc20(to, amount, token_address,  decimal, gas_price)
       return {"tx_hash" : tx_hash}
    else:
        raise UnauthorizedError("not authorized to do this")


@person.method('get_listing')
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

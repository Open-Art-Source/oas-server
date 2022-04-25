import os
from py_crypto_hd_wallet import HdWalletFactory, HdWalletCoins, HdWalletSpecs, HdWalletWordsNum
from bip_utils import Bip39MnemonicGenerator, Bip39SeedGenerator, Bip44, Bip44Coins, Bip44Changes, Bip32
from bip_utils.bip.bip_keys import BipPrivateKey, BipPublicKey, BipPrivateKey
from bip_utils.bip.bip32_utils import Bip32Utils
from hdwallet import HDWallet
from hdwallet.cryptocurrencies import EthereumMainnet
from hdwallet.utils import generate_entropy
from hdwallet.symbols import ETH
import json
import uuid
from typing import Any, Dict, List, Union, NoReturn, Optional, Tuple
import hashlib
import struct
import oas.config as oas_config

py_cryto_hd_wallet_fact = HdWalletFactory(HdWalletCoins.ETHEREUM)

#these are testing, never use in production
_EX_PRIV = 'xprv9zQLLKGwTqVEaQczh1reEnjzrE4xh5U9og2KtFwTLyGNBauV6jBxJhiu9ZKyVSikUV74wsqutdryHyUUmPmtvSTzi5fFpen9pwED6Tzf1Bb'
_EX_PUB = 'xpub6DPgjpoqJD3XnthTo3PebvgjQFuT6YC1AtwvgeM4uJoM4PEdeGWCrW3NzsyeQRsWD8FJvhZMNjyG5HFzAJ1ABkZogGvA4tCgBNLiXL1uaCC'
#must at account level, i.e. hardened so sub-wallet cannot backward tracking to other sub-wallets with private key
_EX_PATH = "m/44'/60'/0'"


def get_address(add_idx:int) -> str:
    return ""

def new_oas_address(user_id:str, use_ex_priv:Optional[bool] = False) -> Tuple[str, str, str]:
    hash = hashlib.md5(user_id.encode('utf-8')).digest()
    path = []
    for i in range(2): 
        a = struct.unpack('<L',hash[i * 4:(i + 1) * 4])
        #for easier referring in the path, can use larger say 10^9 rather than 10^7(total 1TB, assuming no collision)
        idx = a[0] % 1000000
        path.append(idx)
    return make_oas_wallet(path, use_ex_priv)

    #base i.e "m/44'/60'/0'" 
    bip32 = Bip32.FromExtendedKey(oas_config.get("EXTENDED_PUBKEY") if not use_ex_priv else oas_config.get("EXTENDED_PRIVKEY"))
    d_path = oas_config.get("EXTENDED_PATH")
    for i in range(2): 
        a = struct.unpack('<L',hash[i * 4:(i + 1) * 4])
        #for easier referring in the path, can use larger say 10^9 rather than 10^7(total 1TB, assuming no collision)
        idx = a[0] % 1000000
        bip32 = bip32.ChildKey(idx)  
        d_path = d_path + "/" + str(idx)

    #now "m/44'/60'/0'/a1/a2", should be treated as geth like key(i.e. only private key use used, not true HD wallet at this level.
    a = BipPublicKey(bip32, Bip44Coins.ETHEREUM) if not use_ex_priv else BipPrivateKey(bip32, Bip44Coins.ETHEREUM)
    b = a.ToExtended()
    z = py_cryto_hd_wallet_fact.CreateFromExtendedKey("aa", b)
    z.Generate()
    c = z.ToDict()
    return c["addresses"]["address_1"]["address"], d_path, c["addresses"]["address_1"]["raw_priv"] if use_ex_priv else None

def make_oas_wallet(sub_path:List[int], use_ex_priv:Optional[bool] = False) -> Tuple[str, str, str]:
    ex_pub = oas_config.get("EXTENDED_PUBKEY")
    ex_priv = oas_config.get("EXTENDED_PRIVKEY") if use_ex_priv else None
    ex_path = oas_config.get("EXTENDED_PATH")
    return make_subwallet(sub_path, ex_pub, ex_priv, ex_path)

    bip32 = Bip32.FromExtendedKey(oas_config.get("EXTENDED_PUBKEY") if not use_ex_priv else oas_config.get("EXTENDED_PRIVKEY"))
    d_path = oas_config.get("EXTENDED_PATH")
    for i in sub_path: 
        bip32 = bip32.ChildKey(i)  
        d_path = d_path + "/" + str(i)

    #now "m/44'/60'/0'/a1/a2/...", should be treated as geth like key(i.e. only private key use used, not true HD wallet at this level.
    a = BipPublicKey(bip32, Bip44Coins.ETHEREUM) if not use_ex_priv else BipPrivateKey(bip32, Bip44Coins.ETHEREUM)
    b = a.ToExtended()
    z = py_cryto_hd_wallet_fact.CreateFromExtendedKey("aa", b)
    z.Generate()
    c = z.ToDict()
    return c["addresses"]["address_1"]["address"], d_path, c["addresses"]["address_1"]["raw_priv"] if use_ex_priv else None

def make_subwallet(sub_path:List[int], ex_pub:str = None, ex_priv:str = None, ex_path:str = "m/44'/60'/0'") -> Tuple[str, str, str]:
    bip32 = Bip32.FromExtendedKey(ex_priv if ex_priv else ex_pub)
    d_path = ex_path
    for i in sub_path: 
        bip32 = bip32.ChildKey(i)  
        d_path = d_path + "/" + str(i)

    #now "m/44'/60'/0'/a1/a2/...", should be treated as geth like key(i.e. only private key use used, not true HD wallet at this level.
    a = BipPublicKey(bip32, Bip44Coins.ETHEREUM) if not ex_priv else BipPrivateKey(bip32, Bip44Coins.ETHEREUM)
    b = a.ToExtended()
    z = py_cryto_hd_wallet_fact.CreateFromExtendedKey("aa", b)
    z.Generate()
    c = z.ToDict()
    return c["addresses"]["address_1"]["address"], d_path, c["addresses"]["address_1"]["raw_priv"] if ex_priv else None

def new_hdwallet() -> str:
    py_hd_wallet = py_cryto_hd_wallet_fact.CreateRandom("", HdWalletWordsNum.WORDS_NUM_24)
    py_hd_wallet.Generate()
    x = py_hd_wallet.ToDict()
    return dict(mnemonic = x["mnemonic"]
                , path="m/44'/60'/0'/0/0"
                , ex_path = "m/44'/60'/0'"
                , ex_pub=x['account_key']['ex_pub']
                , ex_priv=x['account_key']['ex_priv']
                , address=x["addresses"]["address_1"]["address"]
                , priv=x["addresses"]["address_1"]["raw_priv"]
                , pub=x["addresses"]["address_1"]["raw_uncompr_pub"])

#"m/44'/60'/0'/0/0" would be the 'root' agent wallet, mnemonic imported to HD wallet should produce the same address
MINTER_WALLET = make_oas_wallet([0,0], True)

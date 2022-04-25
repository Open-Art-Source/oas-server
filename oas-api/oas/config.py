import os
from dotenv import load_dotenv

load_dotenv()  # take environment variables from .env.

#these are testing, never use in production
_EX_PRIV = 'xprv9zQLLKGwTqVEaQczh1reEnjzrE4xh5U9og2KtFwTLyGNBauV6jBxJhiu9ZKyVSikUV74wsqutdryHyUUmPmtvSTzi5fFpen9pwED6Tzf1Bb'
_EX_PUB = 'xpub6DPgjpoqJD3XnthTo3PebvgjQFuT6YC1AtwvgeM4uJoM4PEdeGWCrW3NzsyeQRsWD8FJvhZMNjyG5HFzAJ1ABkZogGvA4tCgBNLiXL1uaCC'
#must at account level
_EX_PATH = "m/44'/60'/0'"

def _get(name, ifNone=None):
    val = os.environ.get(name, ifNone)
    if val == 'placeholder': raise Exception("configuration issue {key}".format(key=name))
    return val if val is not None and val != '' and val != 'None' else ifNone

config = dict(
#for firebase services
GOOGLE_CLOUD_PROJECT = _get('GOOGLE_CLOUD_PROJECT','None'),
#for odbc connection
ODBC_CONNECTION_STRING = _get('ODBC_CONNECTION_STRING','DRIVER={ODBC Driver 17 for SQL Server};SERVER=db;PORT=1433;DATABASE=OASDesign;'),
ODBC_CONNECTION_CREDENTIAL = _get('ODBC_CONNECTION_CREDENTIAL','UID=sa;PWD=password;'),
#for sqlalchemy connection
SQLALCHEMY_URL = _get('SQLALCHEMY_URL',"mysql+pymysql://root:password@db/oas?charset=utf8mb4"),
MARIADB_KEY_LOCATION = _get('MARIADB_KEY_LOCATION'),
#for generating custodian wallet keys
EXTENDED_PRIVKEY = _get("EXTENDED_PRIVKEY", _EX_PRIV),
EXTENDED_PUBKEY = _get("EXTENDED_PUBKEY", _EX_PUB),
EXTENDED_PATH = _get("EXTENDED_PATH", _EX_PATH),
#for flask client side cookie encryption
FLASK_SECRET_KEY = _get('FLASK_SECRET_KEY',b'this_is_only_for_test_not_production_use'),
#for redis server
REDIS_URL = _get('REDIS_URL','rediss://db:6379'),
#for api hosting domain
API_HOST = _get('API_HOST','None'),
#for ifps storage service(write) in the form of /dns/<domain>/protocol/port/http like /dns/ipfs.infura.io/tcp/5001/https
IPFS_API_URL = _get('IPFS_API_URL','/dns/db/tcp/5001/http'),
#for ifps storage service(write) credential(say infura), in the form of username:password
IPFS_API_CREDENTIAL = _get('IPFS_API_CREDENTIAL'),
#for ifps http endpoint(read only)
IPFS_BASE_URL = _get('IPFS_BASE_URL','https://ipfs.io/ipfs'),
#firebase service account
FIREBASE_CONFIG_JSON_FILE = _get('FIREBASE_CONFIG_JSON_FILE','d:/oas/oas-api/firebase_service_account.json'),
#web3 rpc
WEB3_RPC_URL = _get('WEB3_RPC_URL', 'https://kovan.infura.io/v3/xxxxxxxxxxxx'),
#proxied erc721 - kovan
NFT_TOKEN_IMPLEMENTATION_ADDRESS = _get('NFT_TOKEN_IMPLEMENTATION_ADDRESS','0x6fda67ae777ac56187a1e656cc66bf10e1a60739'),
#nft token address
#proxy - kovan
NFT_TOKEN_ADDRESS = _get('NFT_TOKEN_ADDRESS','0xca7956861ea939b921da2d793dfc5a6cc5e7a988'),
#goerli
#NFT_TOKEN_ADDRESS = _get('NFT_TOKEN_ADDRESS','0xd79205db887a8686718012b38e1d3bfd042a2475'),
#NFT_TOKEN_ADDRESS = _get('NFT_TOKEN_ADDRESS','0xaFDCC03BCcc8372720c95F8d687096A768D99aB9'),
#NFT_TOKEN_ADDRESS = _get('NFT_TOKEN_ADDRESS','0x7afb1489acbe992e2b3549097491ec1f9e90b2c3'),
#Pytorch model server
#PYTORCH_URL = _get('PYTORCH_URL','http://172.31.20.20/torchserve/predictions/densenet161')
PYTORCH_URL = _get('PYTORCH_URL','http://172.31.20.20/torchserve/predictions'),
PYTORCH_MATCH_URL = _get('PYTORCH_MATCH_URL','http://172.31.20.20/torchserve/predictions/image_dissimilarity'),
PYTORCH_ID_URL = _get('PYTORCH_ID_URL','http://172.31.20.20/torchserve/predictions/densenet161'),
#stacks relay
OAS_STACKS_RPC_URL = _get('OAS_STACKS_RPC_URL','http://localhost:5000/json-rpc'),
OAS_STACKS_NFT_CONTRACT = _get('OAS_STACKS_NFT_CONTRACT','ST3KG5NBY7ABBT1879Q0MCPK3M7YJZHFWJBF9KHKY.Artie'),
#oas chainlink token, kovan
OAS_CHAINLINK_TOKEN_ADDRESS = _get('OAS_CHAINLINK_TOKEN_ADDRESS', '0x3417643c21e5f0744604c48e86482e9419f4e713'),
#oas chainlink operator factory, kovan using 0x3417 as token
OAS_CHAINLINK_OPERATOR_FACTORY_ADDRESS = _get('OAS_CHAINLINK_TOKEN_ADDRESS', '0xc905357377c95925837E3aaA5b0ee2D2a0a87723'),
#oas chainlink operator, kovan using 0x3417 as token
OAS_CHAINLINK_OPERATOR_ADDRESS = _get('OAS_CHAINLINK_TOKEN_ADDRESS', '0xc3F607D98786E12E3b4c4C9Ba47d2262BD27A540'),
)

def get(name, ifNone=None): 
    val = config.get(name)
    if val == 'placeholder': raise Exception("configuration issue {key}".format(key=name))

    return val if val is not None and val != 'None' else ifNone

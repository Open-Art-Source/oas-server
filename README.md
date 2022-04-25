# oas
The OAS application is a mobile centric application which connects the conventional art market with the new NFT world. The objective is to have a easy to use mobile application which allows artists(as well as other players in the market) to create/management and exchange/trade their artworks with NFT(via high resolution image upload). This would create a completely traceable history of any artwork.
# oas-server
server api middle tier that serves as a bridge between mobile/web and blockchains as well as storage(which contains info not suitable for on chain storage)

# components
there are current 3 server side components namely oas-api, pas-pytorch and oas-stacks-relay

# oas-api
this is the main entry point for communicating with the client(mobile/website or other UI). It serves as the connection between the UI application as well as the blockchains and other backend helper functionalities. The main functionalities of the server api are:

1. user info management

The system use google(firebase) authentication for credential management as well as crypto wallet creation(currently using custodian wallet which is more suitable for non-crypto familiar users but can be swtiched to user wallet via metamask/wallet-connect plugin in the UI or other wallet apps in the future)

2. NFT creation

The API server would create NFT token(on the appropriate blockchain)

3. NFT trading/exchange
The API server inteact with the blockchain smart contracts to list/trade users NFTs

oas-api is a python server application using the flask framework using Mariadb(MySql) as the storage backend. Check the seprate readme in the directory for more detail.

#oas-stacks-relay

This is the local nodejs relay that connects to the Stacks blockchain https://www.stacks.co/. Stacks is a smart contract blockchain that lives on bitcoin network rather than the more familiar ethereum one. It is basically the equivalent of L2 layer of ethereum. You can read more about stacks on their main site.

Stacks only provide a typescript/javascript based SDK to connect to their nodes but oher main server(oas-api) is written in python. So we run a relay which provide a more generic api layer(json-rpc) for oas-api to talk to Stacks 

oas-stacks-relay is a nodejs application which is not public facing.

#oas-pytorch

One of the key functionality of OAS is to detect fake/duplicate claim of artworks(creating NFT). We developed a pytorch model which would be run aginst any uploaded image and search for existing registered artworks to identify potential fakes

oas-pytorch is a python application based on Pytorch https://pytorch.org/serve/. The AI model is trained using uploaded images or other image sources
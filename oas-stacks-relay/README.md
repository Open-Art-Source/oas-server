This is nodejs project that serves as a relay between the main oas-api server and the Stacks blockchain https://www.stacks.co/.

The source contracts for the NFT token(oas-nft.clar) and the market place(oas-market.clar) contract is under src/contracts. There is a few ways to deploy them but the easiest in Stacks is via their explorer https://explorer.stacks.co/?chain=mainnet under the sandbox link. This allows you to use their browser plugin for wallet which can track your STX balance as well as FT/NFTs

to run:

npm install
npm start

then configure oas-api accordingly(relay endpoint url and contract addresses)
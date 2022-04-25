//SPDX-License-Identifier: MIT
pragma solidity ^0.8.7;

import "./chainlink/ChainlinkClient.sol";

/**
 * @notice DO NOT USE THIS CODE IN PRODUCTION. This is an example contract. 
 */
contract GenericLargeResponse is ChainlinkClient {
  using Chainlink for Chainlink.Request;

  // variable bytes returned in a signle oracle response
  bytes public data;
  string public image_url;

  /**
   * @notice Initialize the link token and target oracle
   * @dev The oracle address must be an Operator contract for multiword response
   *
   *
   * Kovan Testnet details: 
   * Link Token: 0xa36085F69e2889c224210F603D836748e7dC0088
   * Oracle: 0xc57B33452b4F7BB189bB5AfaE9cc4aBa1f7a4FD8 (Chainlink DevRel)
   *
   */
  constructor(address linkToken, address operatorOracle)
  {
    setChainlinkToken(linkToken);
    setChainlinkOracle(operatorOracle);
  }

  function requestBytes1(
    uint256 payment
  )
    public
  {
    // this is implicitly treated as 0x, i.e. the result is only 16 bytes !!!
    // no documentation in solc mention this!
    // hardcoded, not recommended may be shown as uuid form(with -) in chainlink, must remove all of them
  
    bytes32 specId = "e30f695b833d43b2993fdbe884bc8fbd";
    //uint256 payment = 100000000000000000; // 0.1 LINK
    Chainlink.Request memory req = buildChainlinkRequest(specId, address(this), this.fulfillBytes.selector);
    req.add("url","https://ipfs.io/ipfs/QmZgsvrA1o1C8BGCrx6mHTqR1Ui1XqbCrtbMVrRLHtuPVD?filename=big-api-response.json");
    req.add("path", "result");
    requestOracleData(req, payment);
  }

  function requestBytes2(
    bytes32 specId,
    uint256 payment
  )
    public
  {
    //uint256 payment = 100000000000000000; // 0.1 LINK
    Chainlink.Request memory req = buildChainlinkRequest(specId, address(this), this.fulfillBytes.selector);
    req.add("url","https://ipfs.io/ipfs/QmZgsvrA1o1C8BGCrx6mHTqR1Ui1XqbCrtbMVrRLHtuPVD?filename=big-api-response.json");
    req.add("path", "result");
    requestOracleData(req, payment);
  }

  event RequestFulfilled(
    bytes32 indexed requestId,
    bytes indexed data
  );

  /**
   * @notice Fulfillment function for variable bytes
   * @dev This is called by the oracle. recordChainlinkFulfillment must be used.
   */
  function fulfillBytes(
    bytes32 requestId,
    bytes memory bytesData
  )
    public
    recordChainlinkFulfillment(requestId)
  {
    emit RequestFulfilled(requestId, bytesData);
    data = bytesData;
    image_url = string(data);
  }

}

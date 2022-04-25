//SPDX-License-Identifier: MIT
pragma solidity ^0.8.7;

import "./chainlink/ChainlinkClient.sol";

/**
 * @notice DO NOT USE THIS CODE IN PRODUCTION. This is an example contract. 
 */
contract MultiWordConsumer is ChainlinkClient {
  using Chainlink for Chainlink.Request;

  // variable bytes returned in a signle oracle response
  bytes public data;

  // multiple params returned in a single oracle response
  uint256 public usd;
  uint256 public eur;
  uint256 public jpy;

  /**
   * @notice Initialize the link token and target oracle
   * @dev The oracle address must be an Operator contract for multiword response
   */
  constructor(
    address link,
    address oracle
  ) {
    setChainlinkToken(link);
    setChainlinkOracle(oracle);
  }


  /**
   * @notice Request mutiple parameters from the oracle in a single transaction
   * @param specId bytes32 representation of the jobId in the Oracle
   * @param payment uint256 cost of request in LINK (JUELS)
   */
  function requestMultipleParameters(
    bytes32 specId,
    uint256 payment
  )
    public
  {
    Chainlink.Request memory req = buildChainlinkRequest(specId, address(this), this.fulfillMultipleParameters.selector);
    req.addUint("times", 10000);
    requestOracleData(req, payment);
  }

  /**
   * @notice Request mutiple parameters from the oracle in a single transaction
   * @param specId bytes32 representation of the jobId in the Oracle
   * @param _payment uint256 cost of request in LINK (JUELS)
   */
  function doRequest(bytes32 specId, uint256 _payment) public {
    Chainlink.Request memory req = buildChainlinkRequest(specId, address(this), this.fulfillMultipleParameters.selector);
    req.add("urlUSD", "https://min-api.cryptocompare.com/data/price?fsym=BTC&tsyms=USD,JPY,EUR");
    req.add("pathUSD", "USD");
    req.add("urlEUR", "https://min-api.cryptocompare.com/data/price?fsym=BTC&tsyms=USD,JPY,EUR");
    req.add("pathEUR", "EUR");
    req.add("urlJPY", "https://min-api.cryptocompare.com/data/price?fsym=BTC&tsyms=USD,JPY,EUR");
    req.add("pathJPY", "JPY");
    requestOracleData(req, _payment); // MWR API.
  }
  /**
   * @notice Request mutiple parameters from the oracle in a single transaction
   * @param jobId string representation of the jobId in the Oracle
   * @param _payment uint256 cost of request in LINK (JUELS)
   */

  function doRequest1(string calldata jobId, uint256 _payment) public {
    bytes32 specId;
    bytes memory x = bytes(jobId);
    assembly {
      specId := mload(add(x, 32))
    }

    Chainlink.Request memory req = buildChainlinkRequest(specId, address(this), this.fulfillMultipleParameters.selector);
    req.add("urlUSD", "https://min-api.cryptocompare.com/data/price?fsym=BTC&tsyms=USD,JPY,EUR");
    req.add("pathUSD", "USD");
    req.add("urlEUR", "https://min-api.cryptocompare.com/data/price?fsym=BTC&tsyms=USD,JPY,EUR");
    req.add("pathEUR", "EUR");
    req.add("urlJPY", "https://min-api.cryptocompare.com/data/price?fsym=BTC&tsyms=USD,JPY,EUR");
    req.add("pathJPY", "JPY");
    requestOracleData(req, _payment); // MWR API.
  }

  event RequestMultipleFulfilled(
    bytes32 indexed requestId,
    uint256 indexed usd,
    uint256 indexed eur,
    uint256 jpy
  );

  /**
   * @notice Fulfillment function for multiple parameters in a single request
   * @dev This is called by the oracle. recordChainlinkFulfillment must be used.
   */
  function fulfillMultipleParameters(
    bytes32 requestId,
    uint256 usdResponse,
    uint256 eurResponse,
    uint256 jpyResponse
  )
    public
    recordChainlinkFulfillment(requestId)
  {
    emit RequestMultipleFulfilled(requestId, usdResponse, eurResponse, jpyResponse);
    usd = usdResponse;
    eur = eurResponse;
    jpy = jpyResponse;
  }
}

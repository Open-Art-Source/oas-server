// SPDX-License-Identifier: MIT
pragma solidity ^0.8.7;

import "./chainlink/ChainlinkClient.sol";
import "./chainlink/interfaces/LinkTokenInterface.sol";
import "./Owned.sol";

/**
 * @notice DO NOT USE THIS CODE IN PRODUCTION. This is an example contract. 
 */
contract MultiRequestConsumer is ChainlinkClient, Owned {
  using Chainlink for Chainlink.Request;

  uint256 private requestCount = 1;
  LinkTokenInterface private link;

  struct Request {
    bytes32 id;
    int256[] submissions;
    uint8 asked;
    uint8 replied;
  }

  mapping(bytes32 => Request) public request;
  mapping(bytes32 => bytes32) public id2req;
  mapping(bytes32 => string) public nodeSpec;
  mapping(bytes32 => uint16) public nodeIdx;
  bytes32[] public nodes;

  event RequestMultipleFulfilled(
    bytes32 indexed reqId,
    bytes32 indexed requestId,
    address indexed fulfilledBy,
    int256 response
  );

  event RequestSubmitted(address indexed sender, bytes32 requestId);

  /**
   * @notice Initialize the link token and target oracle
   * @dev The oracle address must be an Operator contract for multiword response
   */
  constructor(
    address _link,
    address oracle
  ) Owned() {
    setChainlinkToken(_link);
    setChainlinkOracle(oracle);
    link = LinkTokenInterface(_link);
  }



  /**
   * @notice Request mutiple runs from the oracle in a single transaction
   * @param specIds bytes32[] representation of the jobIds in the Oracle
   * @param _payment uint256 cost of request in LINK (JUELS)
   * @param urls url for each job
   * @param resultPath returned json walk path
   */
  function ownerRequest(bytes32[] calldata specIds, uint256 _payment, string[] calldata urls, string calldata resultPath) public onlyOwner returns(bytes32) {
    require(specIds.length == urls.length && specIds.length > 0,"#specId==#urls && >0");
    bytes32 requestId = keccak256(abi.encodePacked(this, requestCount));
    // payment from caller requires approval before calling this
    bool paid = link.transferFrom(msg.sender, address(this), 1);
    require(paid,"payment failed");
    
    Request memory nextRequest = Request(
      requestId,
      new int256[](0),
      uint8(specIds.length),
      0
    );
    request[requestId] = nextRequest;
    requestCount += 1;
    
    for (uint256 i = 0; i < specIds.length; i++) {
      bytes32 req = _makeRequest(specIds[i], _payment, urls[i], resultPath);
      id2req[req] = requestId;
    }

    emit RequestSubmitted(msg.sender, requestId);
    return requestId;
  }

/**
   * @notice Request mutiple runs from the oracle in a single transaction
   * @param queryString query string append to pre-set url
   * @param resultPath returned json walk path
   * @param _payment uint256 cost of request in LINK (JUELS)
   */
  function doRequest(string calldata queryString, string calldata resultPath, uint256 _payment, uint256 quorum) public returns(bytes32) {
    bytes32 requestId = keccak256(abi.encodePacked(this, requestCount));
    // payment from caller requires approval before calling this
    bool paid = link.transferFrom(msg.sender, address(this), 1);
    require(paid,"payment failed");
    quorum = quorum == 0 ? 1 : quorum;
    quorum = quorum > nodes.length ?  nodes.length : quorum;
    require(quorum > 0, "no running nodes");
    Request memory nextRequest = Request(
      requestId,
      new int256[](0),
      uint8(quorum),
      0
    );
    request[requestId] = nextRequest;
    requestCount += 1;
    
    for (uint256 i = 0; i < quorum; i++) {
      bytes32 specId = nodes[i];
      string memory url = string(abi.encodePacked(nodeSpec[specId], "?", queryString)); 
      bytes32 req = _makeRequest(specId, _payment, url, resultPath);
      id2req[req] = requestId;
    }

    emit RequestSubmitted(msg.sender, requestId);
    return requestId;
  }


  /**
   * @notice Fulfillment function 
   * @dev This is called by the oracle. recordChainlinkFulfillment must be used.
   */
  function fulfillMultipleParameters(
    bytes32 requestId,
    int256 response
  )
    public
    recordChainlinkFulfillment(requestId)
  {

    bytes32 reqId = id2req[requestId];

    require(reqId != 0,"invalid fulfillment");
    Request storage req = request[reqId];
    require(req.replied < req.asked, "request already fulfilled");
    req.submissions.push(response);
    req.replied += 1;
    delete id2req[requestId];

    emit RequestMultipleFulfilled(reqId, requestId, tx.origin, response);

  }

  function withdrawFund(uint256 amount) public onlyOwner {
    uint256 balance = link.balanceOf(address(this));
    require(amount <= balance, "insufficient balance");
    link.transfer(msg.sender, amount > 0 ? amount : balance);
  }
  
  function setSpecId(bytes32 specId, string calldata baseUrl) public onlyOwner {
    require(specId > 0, "specId empty");
    uint16 idx = nodeIdx[specId];
    if (bytes(baseUrl).length == 0) {
      require(idx > 0, "unknown specId");
      bytes32 lastSpecId = nodes[nodes.length - 1];
      if (lastSpecId != specId) {
        nodes[idx] = lastSpecId;
        nodeIdx[lastSpecId] = idx;
      }
      nodes.pop();
      delete nodeIdx[specId];
      delete nodeSpec[specId];
    }
    else {
      if (idx == 0) {
        nodes.push(specId);
        nodeIdx[specId] = uint16(nodes.length);
      }
      nodeSpec[specId] = baseUrl;
    }
  }

  function requestResult(bytes32 requestId) public view returns(int256[] memory, uint8) {
    Request memory req = request[requestId];
    return (req.submissions, req.asked);
  }
  
  // private functions
  function _makeRequest(bytes32 specId, uint256 _payment, string memory url, string memory resultPath) private returns(bytes32) {
    Chainlink.Request memory req = buildChainlinkRequest(specId, address(this), this.fulfillMultipleParameters.selector);
    req.add("url", url);
    req.add("resultPath", resultPath);
    bytes32 requestId = requestOracleData(req, _payment); 
    return requestId;
  }

}
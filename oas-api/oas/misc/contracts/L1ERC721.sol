// SPDX-License-Identifier: MIT
pragma solidity >= 0.8;
// @unsupported: ovm
import {ERC721} from "../openzeppelin/contracts/token/ERC721/ERC721.sol";
import {ERC721URIStorage} from "../openzeppelin/contracts/token/ERC721/extensions/ERC721URIStorage.sol";
import {ERC721Pausable} from "../openzeppelin/contracts/token/ERC721//extensions/ERC721Pausable.sol";
import {ERC721Enumerable} from "../openzeppelin/contracts/token/ERC721//extensions/ERC721Enumerable.sol";
import {ERC721Burnable} from "../openzeppelin/contracts/token/ERC721//extensions/ERC721Burnable.sol";
import {AccessControlEnumerable} from "../openzeppelin/contracts/access/AccessControlEnumerable.sol";
import {Counters} from "../openzeppelin/contracts/utils/Counters.sol";
/**
 * @dev {ERC721} token, including:
 *
 *  - ability for holders to burn (destroy) their tokens
 *  - a minter role that allows for token minting (creation)
 *  - a pauser role that allows to stop all token transfers
 *  - token ID and URI autogeneration
 *
 * This contract uses {AccessControl} to lock permissioned functions using the
 * different roles - head to its documentation for details.
 *
 * The account that deploys the contract will be granted the minter and pauser
 * roles, as well as the default admin role, which will let it grant both minter
 * and pauser roles to other accounts.
 */
contract L1ERC721 is AccessControlEnumerable, ERC721Burnable, ERC721Enumerable, ERC721Pausable, ERC721URIStorage {
    using Counters for Counters.Counter;

    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");
    
    Counters.Counter private _tokenIdTracker;

    /**
     * @dev Emitted when `tokenId` token metadata changed.
     */
    event SetTokenURI(uint256 indexed tokenId, address indexed owner, string oldTokenURI, string tokenURI);

    /**
     * @dev Emitted when `tokenId` is minted and offchainId supplied
     */
    event Minted(uint256 indexed tokenId, uint256 indexed offchainId, address indexed to);

    /**
     * @dev Grants `DEFAULT_ADMIN_ROLE`, `MINTER_ROLE` and `PAUSER_ROLE` to the
     * account that deploys the contract.
     *
     * Token URIs will be autogenerated based on `baseURI` and their token IDs.
     * See {ERC721-tokenURI}.
     */
    constructor(string memory name, string memory symbol) ERC721(name, symbol) {
        _setupRole(DEFAULT_ADMIN_ROLE, _msgSender());
        _setupRole(MINTER_ROLE, _msgSender());
        _setupRole(PAUSER_ROLE, _msgSender());
    }

    /**
     * @dev Creates a new token for `to`. Its token ID will be automatically
     * assigned (and available on the emitted {IERC721-Transfer} event), 
     * offchainId is used to match auto assigned token ID(offchain matching)
     * See {ERC721-_mint}.
     *
     * Requirements:
     *
     * - the caller must have the `MINTER_ROLE` or can only mint to self.
     */
    function mint(address to, string memory _tokenURI, uint256 offchainId) public virtual {
        require(hasRole(MINTER_ROLE, _msgSender())  || to == _msgSender(), "L1ERC721: must have minter role to mint for others");
        require(bytes(_tokenURI).length > 0, "L1ERC721: must supply _tokenURI");

        _tokenIdTracker.increment();
        uint256 tokenId = _tokenIdTracker.current();
        _safeMint(to, tokenId);
        _setTokenURI(tokenId, _tokenURI);
        if (offchainId != 0) {
            emit Minted(tokenId, offchainId, to);
        }
    }

    /**
     * @dev Creates a new token for `to`. token ID is supplied(which must not exist, should use some form of hash)
     *
     * See {ERC721-_mint}.
     *
     * Requirements:
     *
     * - the caller must have the `MINTER_ROLE` or can only mint to self.
     */
    function mintWith(address to, string memory _tokenURI, uint256 offchainId) public virtual {
        require(hasRole(MINTER_ROLE, _msgSender())  || to == _msgSender(), "L1ERC721: must have minter role to mint for others");
        require(bytes(_tokenURI).length > 0, "L1ERC721: must supply _tokenURI");
        require(offchainId > 1000000000000 && !_exists(offchainId), "L1ERC721: must supply fresh offchainId(>1000000000000) to mint");
        require(bytes(tokenURI(offchainId)).length == 0, "L1ERC721: supplied offchainId already exists");

        uint256 tokenId = offchainId;
        _safeMint(to, tokenId);
        _setTokenURI(tokenId, _tokenURI);
        emit Minted(tokenId, offchainId, to);

    }

    function setTokenURI(uint256 tokenId, string memory newTokenURI) public {
        address sender = _msgSender();
        require(ownerOf(tokenId) == sender, "L1ERC721: only owner can change tokenURI");
        emit SetTokenURI(tokenId, sender, tokenURI(tokenId), newTokenURI);
        _setTokenURI(tokenId, newTokenURI);
    }

    function makeOffchainId(string calldata offchainRef) public pure returns(bytes32) {
        return keccak256(abi.encodePacked(offchainRef));        
    }
    
    /**
     * @dev See {IERC721Metadata-tokenURI}.
     */
    function tokenURI(uint256 tokenId) public view virtual override(ERC721, ERC721URIStorage) returns (string memory) {
        return super.tokenURI(tokenId);
    }
    /**
     * @dev Destroys `tokenId`.
     * The approval is cleared when the token is burned.
     *
     * Requirements:
     *
     * - `tokenId` must exist.
     *
     * Emits a {Transfer} event.
     */
    function _burn(uint256 tokenId) internal virtual override(ERC721, ERC721URIStorage) {
        super._burn(tokenId);
    }

    /**
     * @dev Pauses all token transfers.
     *
     * See {ERC721Pausable} and {Pausable-_pause}.
     *
     * Requirements:
     *
     * - the caller must have the `PAUSER_ROLE`.
     */
    function pause() public virtual {
        require(hasRole(PAUSER_ROLE, _msgSender()), "L1ERC721: must have pauser role to pause");
        _pause();
    }

    /**
     * @dev Unpauses all token transfers.
     *
     * See {ERC721Pausable} and {Pausable-_unpause}.
     *
     * Requirements:
     *
     * - the caller must have the `PAUSER_ROLE`.
     */
    function unpause() public virtual {
        require(hasRole(PAUSER_ROLE, _msgSender()), "L1ERC721: must have pauser role to unpause");
        _unpause();
    }

    function _beforeTokenTransfer(address from, address to, uint256 tokenId) internal virtual override(ERC721, ERC721Enumerable, ERC721Pausable) {
        super._beforeTokenTransfer(from, to, tokenId);
    }

    /**
     * @dev See {IERC165-supportsInterface}.
     */
    function supportsInterface(bytes4 interfaceId) public view virtual override(AccessControlEnumerable, ERC721, ERC721Enumerable) returns (bool) {
        return super.supportsInterface(interfaceId);
    }
}
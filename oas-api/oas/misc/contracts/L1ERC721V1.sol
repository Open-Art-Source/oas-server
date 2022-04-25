// SPDX-License-Identifier: MIT
pragma solidity >=0.8;
// @unsupported: ovm
import {UUPSUpgradeable} from "../openzeppelin-upgradeable/contracts/proxy/utils/UUPSUpgradeable.sol";
import {ERC721Upgradeable} from "../openzeppelin-upgradeable/contracts/token/ERC721/ERC721Upgradeable.sol";
import {ERC721URIStorageUpgradeable} from "../openzeppelin-upgradeable/contracts/token/ERC721/extensions/ERC721URIStorageUpgradeable.sol";
import {ERC721PausableUpgradeable} from "../openzeppelin-upgradeable/contracts/token/ERC721//extensions/ERC721PausableUpgradeable.sol";
import {ERC721EnumerableUpgradeable} from "../openzeppelin-upgradeable/contracts/token/ERC721//extensions/ERC721EnumerableUpgradeable.sol";
import {ERC721BurnableUpgradeable} from "../openzeppelin-upgradeable/contracts/token/ERC721//extensions/ERC721BurnableUpgradeable.sol";
import {AccessControlEnumerableUpgradeable} from "../openzeppelin-upgradeable/contracts/access/AccessControlEnumerableUpgradeable.sol";
import {CountersUpgradeable} from "../openzeppelin-upgradeable/contracts/utils/CountersUpgradeable.sol";

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

/* DO NOT CHANGE ORDER OF subclass(is ...) as many have their own storage
 */
contract L1ERC721V1 is
    AccessControlEnumerableUpgradeable,
    ERC721BurnableUpgradeable,
    ERC721EnumerableUpgradeable,
    ERC721PausableUpgradeable,
    ERC721URIStorageUpgradeable,
    UUPSUpgradeable
{
    /* this is the equivalent of constructor, but only work ONCE
     * i.e. version 0 of the implmentation(when called by the proxy constructor)
     * all future upgrade(with modifier initializer) would be skipped
     * as the state is stored in the proxy as initialized
     * use another function like upgrade() on subsequent upgradeAndCall()
     */
    function initialize(
        string memory name,
        string memory symbol,
        string memory baseTokenURI
    ) public virtual initializer {
        __ERC721PresetMinterPauserAutoId_init(name, symbol, baseTokenURI);
    }
    /**
     * @dev Grants `DEFAULT_ADMIN_ROLE`, `MINTER_ROLE`, `UPGRADER_ROLE` and `PAUSER_ROLE` to the
     * account that deploys the contract.
     *
     * Token URIs will be autogenerated based on `baseURI` and their token IDs.
     * See {ERC721-tokenURI}.
     */
    function __ERC721PresetMinterPauserAutoId_init(
        string memory name,
        string memory symbol,
        string memory baseTokenURI
    ) internal initializer {
        __Context_init_unchained();
        __ERC165_init_unchained();
        __AccessControl_init_unchained();
        __AccessControlEnumerable_init_unchained();
        __ERC721_init_unchained(name, symbol);
        __ERC721Enumerable_init_unchained();
        __ERC721Burnable_init_unchained();
        __Pausable_init_unchained();
        __ERC721Pausable_init_unchained();
        __ERC721PresetMinterPauserAutoId_init_unchained(baseTokenURI);
    }

    function __ERC721PresetMinterPauserAutoId_init_unchained(
        string memory baseTokenURI
    ) internal initializer {
        /* do not set this or it becomes concat and if the setTokenUri call supplied
         * full url, everything would be wrong

        _baseTokenURI = baseTokenURI;
        */
        // noop to bypass warning
        baseTokenURI = baseTokenURI;

        _setupRole(DEFAULT_ADMIN_ROLE, _msgSender());

        _setupRole(MINTER_ROLE, _msgSender());
        _setupRole(PAUSER_ROLE, _msgSender());
        _setupRole(UPGRADE_ROLE, _msgSender());
    }

    /* UUPSUpgradeable interface required function */
    // Not having any checks in this function is dangerous! Do not do this outside tests!
    function _authorizeUpgrade(address) internal virtual override {
        require(
            hasRole(UPGRADE_ROLE, _msgSender()),
            "L1ERC721V1: only address with upgrade role can upgrade"
        );

    }
    /* end of UUPSUpgradeable required function */

    using CountersUpgradeable for CountersUpgradeable.Counter;

    /* start of storage, DO NOT CHANGE ORDER OR CHANGE TYPE OR DELETE(to preseve layout of older version), ONLY APPEND!!!! */

    bytes32 public constant MINTER_ROLE = keccak256("MINTER_ROLE");
    bytes32 public constant PAUSER_ROLE = keccak256("PAUSER_ROLE");
    bytes32 public constant UPGRADE_ROLE = keccak256("UPGRADE_ROLE");

    CountersUpgradeable.Counter private _tokenIdTracker;

    string private _baseTokenURI;

    /* storage end */
    /**
     * @dev Emitted when `tokenId` token metadata changed.
     */
    event SetTokenURI(
        uint256 indexed tokenId,
        address indexed owner,
        string oldTokenURI,
        string tokenURI
    );

    /**
     * @dev Emitted when `tokenId` is minted and offchainId supplied
     */
    event Minted(
        uint256 indexed tokenId,
        uint256 indexed offchainId,
        address indexed to
    );

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
    function mint(
        address to,
        string memory _tokenURI,
        uint256 offchainId
    ) public virtual {
        require(
            hasRole(MINTER_ROLE, _msgSender()) || to == _msgSender(),
            "L1ERC721V1: must have minter role to mint for others"
        );
        require(bytes(_tokenURI).length > 0, "L1ERC721V1: must supply _tokenURI");

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
    function mintWith(
        address to,
        string memory _tokenURI,
        uint256 offchainId
    ) public virtual {
        require(
            hasRole(MINTER_ROLE, _msgSender()) || to == _msgSender(),
            "L1ERC721V1: must have minter role to mint for others"
        );
        require(bytes(_tokenURI).length > 0, "L1ERC721V1: must supply _tokenURI");
        require(
            offchainId > 1000000000000 && !_exists(offchainId),
            "L1ERC721V1: must supply fresh offchainId(>1000000000000) to mint"
        );
        require(
            bytes(tokenURI(offchainId)).length == 0,
            "L1ERC721V1: supplied offchainId already exists"
        );

        uint256 tokenId = offchainId;
        _safeMint(to, tokenId);
        _setTokenURI(tokenId, _tokenURI);
        emit Minted(tokenId, offchainId, to);
    }

    function setTokenURI(uint256 tokenId, string memory newTokenURI) public {
        address sender = _msgSender();
        require(
            ownerOf(tokenId) == sender,
            "L1ERC721V1: only owner can change tokenURI"
        );
        emit SetTokenURI(tokenId, sender, tokenURI(tokenId), newTokenURI);
        _setTokenURI(tokenId, newTokenURI);
    }

    function makeOffchainId(string calldata offchainRef)
        public
        pure
        returns (bytes32)
    {
        return keccak256(abi.encodePacked(offchainRef));
    }

    /**
     * @dev See {IERC721Metadata-tokenURI}.
     */
    function tokenURI(uint256 tokenId)
        public
        view
        virtual
        override(ERC721Upgradeable, ERC721URIStorageUpgradeable)
        returns (string memory)
    {
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
    function _burn(uint256 tokenId)
        internal
        virtual
        override(ERC721Upgradeable, ERC721URIStorageUpgradeable)
    {
        super._burn(tokenId);
    }

    /**
     * @dev Pauses all token transfers.
     *
     * See {ERC721PausableUpgradeable} and {Pausable-_pause}.
     *
     * Requirements:
     *
     * - the caller must have the `PAUSER_ROLE`.
     */
    function pause() public virtual {
        require(
            hasRole(PAUSER_ROLE, _msgSender()),
            "L1ERC721V1: must have pauser role to pause"
        );
        _pause();
    }

    /**
     * @dev Unpauses all token transfers.
     *
     * See {ERC721PausableUpgradeable} and {Pausable-_unpause}.
     *
     * Requirements:
     *
     * - the caller must have the `PAUSER_ROLE`.
     */
    function unpause() public virtual {
        require(
            hasRole(PAUSER_ROLE, _msgSender()),
            "L1ERC721V1: must have pauser role to unpause"
        );
        _unpause();
    }

    function _beforeTokenTransfer(
        address from,
        address to,
        uint256 tokenId
    )
        internal
        virtual
        override(
            ERC721Upgradeable,
            ERC721EnumerableUpgradeable,
            ERC721PausableUpgradeable
        )
    {
        super._beforeTokenTransfer(from, to, tokenId);
    }

    /**
     * @dev See {IERC165-supportsInterface}.
     */
    function supportsInterface(bytes4 interfaceId)
        public
        view
        virtual
        override(
            AccessControlEnumerableUpgradeable,
            ERC721Upgradeable,
            ERC721EnumerableUpgradeable
        )
        returns (bool)
    {
        return super.supportsInterface(interfaceId);
    }
}

;; Import
;; trait to implement
;; on mainnet
;;(use-trait nft-trait 'SP2PABAF9FTAJYNFZH93XENAJ8FVY99RRM50D2JG9.nft-trait.nft-trait)
;; on testnet
;;(use-trait nft-trait 'ST2PABAF9FTAJYNFZH93XENAJ8FVY99RRM4DF2YCW.nft-trait.nft-trait)
;; local
;;(use-trait nft-trait .nft-trait.nft-trait)

(define-trait oas-nft-trait
  (
    ;; Last token ID, limited to uint range
    (get-last-token-id () (response uint uint))

    ;; URI for metadata associated with the token
    (get-token-uri (uint) (response (optional (string-ascii 256)) uint))

     ;; Owner of a given token identifier
    (get-owner (uint) (response (optional principal) uint))

    ;; Transfer from the sender to a new principal
    (transfer (uint principal principal) (response bool uint))
    
    ;; Transfer from owner to a new principal
    (transfer-from  (uint principal principal) (response bool uint))

    ;; enable operator to transfer on behave of
    (set-operator-approval (principal bool) (response bool uint))

    ;; enable spender to transfer token-id on behave of
    (set-spender-approval (principal uint) (response uint uint))

  )
)

;; Storage

;; Store contract admins(simulate ethereum only_owner like usage)
(define-map admins principal bool)

;; # of admin, control accidental removing all admins
(define-data-var admin-count uint u0)

(define-map listing
  (tuple (nft-contract principal) (seller principal) (token-id uint))
  (tuple (price uint) (buyer (optional principal)) (status uint))
)

(define-map order-list
  (tuple (nft-contract principal) (token-id uint))
  (tuple (block-number uint) (seller principal) (buyer principal) (status uint))
)

;; Read only
(define-read-only (get-errstr (code uint))
  (unwrap! (map-get? err-strings (err code)) "unknown-error"))

(define-read-only (is-admin)
  (or
    (default-to false (map-get? admins tx-sender))
    (default-to false (map-get? admins contract-caller))
  )
)

(define-read-only (get-item (seller principal) (token-id uint) (nft-contract <oas-nft-trait>))
    ;; doesn't work for cross-contract via trait
    ;; (contract-call? nft-contract get-owner token-id)
    (map-get? listing {nft-contract: (contract-of nft-contract), seller: seller, token-id: token-id})
)

(define-read-only (get-order (token-id uint) (nft-contract <oas-nft-trait>))
    (map-get? order-list {nft-contract: (contract-of nft-contract), token-id: token-id})
)


;; Public

(define-public (list-item (token-id uint) (price uint) (nft-contract <oas-nft-trait>))
    (let (
        (token-owner (unwrap! (unwrap! (contract-call? nft-contract get-owner token-id) (err u1234)) (err u1235)))
        (item (map-get? listing {nft-contract: (contract-of nft-contract), seller: tx-sender, token-id: token-id}))
        (this-contract (as-contract tx-sender))
        )
        (asserts! (is-eq token-owner tx-sender) nft-not-owned-err)
        (asserts! (or (is-eq item none) (is-eq (default-to u0 (get status item)) item-avail)) nft-not-owned-err)
        (map-set listing 
            {nft-contract: (contract-of nft-contract), seller: tx-sender,  token-id: token-id} 
            {price: price, buyer: none, status: item-avail})
        ;; do not wrap with as-contract so the tx-sender is the signer(i.e owner) not this contract
        ;; alternative is once off spender
        (contract-call? nft-contract set-operator-approval this-contract true)
        ;;(ok true)
    )
)

(define-public (delist-item (token-id uint) (nft-contract <oas-nft-trait>))
    (let (
        (item (unwrap! (map-get? listing {nft-contract: (contract-of nft-contract), seller: tx-sender, token-id: token-id}) (err u1234)))
        )
        (asserts! (is-eq (get status item) item-avail) item-not-avail)
        (map-delete listing {nft-contract: (contract-of nft-contract), seller: tx-sender,  token-id: token-id})
        ;; we don't reset operator approval once set
        ;; if use spender, should reset here
        (ok true)
    )
)

(define-public (purchase-item (token-id uint) (nft-contract <oas-nft-trait>))
    (let (
        (token-owner (unwrap! (unwrap! (contract-call? nft-contract get-owner token-id) (err u1234)) (err u1235)))
        (item (unwrap! (map-get? listing {nft-contract: (contract-of nft-contract), seller: token-owner, token-id: token-id}) (err u1236)))
        (this-contract (as-contract tx-sender))
        (token-recipient this-contract)
        (stx-recipient this-contract)
        (price (get price item))
        )
        (asserts! (is-eq (get status item) item-avail) item-not-avail)
        (unwrap! (as-contract (contract-call? nft-contract transfer-from token-id token-owner token-recipient)) (err u1237))
        (unwrap! (stx-transfer? price tx-sender stx-recipient) (err u1238))
        (map-set listing 
            {seller: token-owner, nft-contract: (contract-of nft-contract), token-id: token-id}
            (merge item { buyer: (some tx-sender), status: item-reserved})
            )
        (map-set order-list 
            {nft-contract: (contract-of nft-contract), token-id: token-id}
            {block-number: block-height, buyer: tx-sender, seller: token-owner, status: item-reserved}
            )
        (print { action: "purchase-order", price: price, seller: token-owner, buyer: tx-sender, token-id: token-id, contract: (contract-of nft-contract)})
        (ok true)
    )
)

(define-public (item-sent (token-id uint) (nft-contract <oas-nft-trait>))
    (let (
        (order (unwrap! (map-get? order-list {nft-contract: (contract-of nft-contract), token-id: token-id}) (err u1234)))
        (seller (get seller order))
        (this-contract (as-contract tx-sender))
        (token-owner (unwrap! (unwrap! (contract-call? nft-contract get-owner token-id) (err u1235)) (err u1236)))
        )
        (asserts! (is-eq seller tx-sender) (err u1237))
        (asserts! (is-eq token-owner this-contract) (err u1238))
        (map-set order-list 
            {nft-contract: (contract-of nft-contract), token-id: token-id}
            (merge order { status: item-shipped})
            )
        (print { action: "item-sent", seller: seller, buyer: (get buyer order), token-id: token-id, contract: (contract-of nft-contract)})
        (ok true)
    )
)

(define-public (confirm-item (token-id uint) (nft-contract <oas-nft-trait>))
    (let (
        (order (unwrap! (map-get? order-list {nft-contract: (contract-of nft-contract), token-id: token-id}) (err u1234)))
        (seller (get seller order))
        (item (unwrap! (map-get? listing {nft-contract: (contract-of nft-contract), seller: seller, token-id: token-id}) (err u1235)))
        (this-contract (as-contract tx-sender))
        (token-recipient (unwrap! (get buyer item) (err u1236)))
        (stx-recipient seller)
        (price (get price item))
        )
        (unwrap! (as-contract (contract-call? nft-contract transfer token-id this-contract token-recipient)) (err u1237))
        (try! (as-contract (stx-transfer? price this-contract stx-recipient)))
        (map-delete listing {seller: seller, nft-contract: (contract-of nft-contract), token-id: token-id})
        (map-delete order-list {nft-contract: (contract-of nft-contract), token-id: token-id})
        (print { action: "purchase", price: price, seller: seller, buyer: token-recipient, token-id: token-id, contract: (contract-of nft-contract)})
        (ok true)
    )
)

(define-public (reject-item (token-id uint) (nft-contract <oas-nft-trait>))
    (let (
        (order (unwrap! (map-get? order-list {nft-contract: (contract-of nft-contract), token-id: token-id}) (err u1234)))
        (seller (get seller order))
        (buyer (get buyer order))
        (item (unwrap! (map-get? listing {nft-contract: (contract-of nft-contract), seller: seller, token-id: token-id}) (err u1235)))
        )
        (asserts! (is-eq buyer tx-sender) (err u1236))
        (map-set order-list 
            {nft-contract: (contract-of nft-contract), token-id: token-id}
            (merge order { status: item-dispute})
            )
        (print { action: "dispute", seller: seller, buyer: buyer, token-id: token-id, contract: (contract-of nft-contract)})
        (ok true)
    )
)

(define-public (resolve-order-dispute (to-buyer uint) (to-seller uint) (token-id uint) (nft-contract <oas-nft-trait>))

    (let (
        (order (unwrap! (map-get? order-list {nft-contract: (contract-of nft-contract), token-id: token-id}) (err u1234)))
        (seller (get seller order))
        (item (unwrap! (map-get? listing {nft-contract: (contract-of nft-contract), seller: seller, token-id: token-id}) (err u1235)))
        (buyer (unwrap! (get buyer item) (err u1237)))
        (this-contract (as-contract tx-sender))
        (price (get price item))
        )
        (asserts! (is-admin) not-admin-err)
        (asserts! (is-eq price (+ to-buyer to-seller)) mismatch-unwind-err)
        (unwrap! (as-contract (contract-call? nft-contract transfer-from token-id this-contract seller)) (err u1238))
        (unwrap! (as-contract (stx-transfer? to-seller this-contract seller)) (err u1239))
        (unwrap! (as-contract (stx-transfer? to-buyer this-contract buyer)) (err u1240))
        (map-delete listing {seller: seller, nft-contract: (contract-of nft-contract), token-id: token-id})
        (map-delete order-list {nft-contract: (contract-of nft-contract), token-id: token-id})
        (print { action: "resolve-dispute", price: price, seller: seller, buyer: buyer, token-id: token-id, contract: (contract-of nft-contract)})
        (ok true)
    )
)

;; one step purchase
(define-public (purchase-item-direct (token-id uint) (nft-contract <oas-nft-trait>))
    (let (
        (token-owner (unwrap! (unwrap! (contract-call? nft-contract get-owner token-id) (err u1235)) (err u1236)))
        (item (unwrap! (get-item token-owner token-id nft-contract) (err u1234)))
        ;;(item (unwrap-panic (map-get? listing {nft-contract: (contract-of nft-contract), seller: token-owner, token-id: token-id})))
        (buyer tx-sender)
        (price (get price item))
        )
        (asserts! (is-eq (get status item) item-avail) item-not-avail)
        (unwrap! (as-contract (contract-call? nft-contract transfer-from token-id token-owner buyer)) (err u1237))
        (unwrap! (stx-transfer? price tx-sender token-owner) (err u1238))
        (map-delete listing {seller: token-owner, nft-contract: (contract-of nft-contract), token-id: token-id})
        (print { action: "purchase-direct", price: price, seller: token-owner, buyer: buyer, token-id: token-id, contract: (contract-of nft-contract)})
        (ok true)
    )
)

;; Private
;; for testing only turned to private now
(define-private (purchase (token-owner principal) (token-id uint) (price uint) (contract <oas-nft-trait>))
    (let (
        (recipient tx-sender)
        )
        (unwrap-panic (as-contract (contract-call? contract transfer-from token-id token-owner recipient)))
        (unwrap-panic (stx-transfer? price tx-sender token-owner))
        (ok true)
    )
)

;; listing status
(define-constant item-avail u0)
(define-constant item-reserved u1)
(define-constant item-shipped u2)
(define-constant item-dispute u3)

;; error handling
(define-constant nft-not-owned-err (err u401)) ;; unauthorized
(define-constant not-admin-err (err u403)) ;; forbidden
(define-constant no-admin-err (err u403)) ;; forbidden
(define-constant nft-not-found-err (err u404)) ;; not found
(define-constant nft-exists-err (err u409)) ;; conflict

(define-constant item-not-avail (err u100)) ;; item is listed but in transit state
(define-constant mismatch-unwind-err (err u101)) ;; dispute resolution amount not correct

(define-map err-strings (response uint uint) (string-ascii 32))
(map-insert err-strings nft-not-owned-err "nft-not-owned")
(map-insert err-strings not-admin-err "not-admin")
(map-insert err-strings no-admin-err "no-admin")
(map-insert err-strings nft-not-found-err "nft-not-found")
(map-insert err-strings nft-exists-err "nft-exists")


;; Initialize the contract
(begin
  (map-set admins tx-sender true)
  (var-set admin-count u1)
  )

;; Implement the `ft-trait` trait defined in the `ft-trait` contract
;;mainnet
;;(impl-trait 'SP3FBR2AGK5H9QBDH3EEN6DF8EK8JY7RX8QJ5SVTE.sip-010-trait-ft-standard.sip-010-trait)
;;testnet
;;(impl-trait 'ST3KG5NBY7ABBT1879Q0MCPK3M7YJZHFWJBF9KHKY.sip-010-trait-ft-standard.sip-010-trait)
;; local
(impl-trait .sip-010-trait-ft-standard.sip-010-trait)

(define-fungible-token oas-token (* u1000000 u1000000000))
(define-constant init-amount (* u1000000 u1000000))

;; Storage

;; spender
(define-map tokens-spender
  (tuple (owner principal) (spender principal))
  uint
)

;; Store contract admins(simulate ethereum only_owner like usage)
(define-map admins principal bool)

;; # of admin, control accidental removing all admins
(define-data-var admin-count uint u0)

(define-data-var paused bool false)

(define-data-var token-uri (string-utf8 256) u"https://openartsource.io/oas-token/meta.json")

;;(define-data-var stx-token-rate (tuple (num uint) (denom uint)) {num: (- u1000000 u50000), denom: u1000000})
(define-data-var stx-token-rate (tuple (num uint) (denom uint)) {num: u100, denom: u1}) ;; 1 stx -> 100 token

(define-data-var issued uint u0)
;; sip-010 required trait
(define-read-only (get-total-supply)
  (ok (ft-get-supply oas-token))
)

(define-read-only (get-name)
  (ok "OAS Token")
)

(define-read-only (get-symbol)
  (ok "ACORN")
)

(define-read-only (get-decimals)
  (ok u6)
)

(define-read-only (get-balance (account principal))
  (ok (ft-get-balance oas-token account))
)

(define-public (transfer (amount uint) (sender principal) (recipient principal) (memo (optional (buff 34))))
  (begin
    (asserts! (can-transfer tx-sender sender amount) (err u403))
    (asserts! (not (is-eq sender recipient)) (err u1235))
    (match (ft-transfer? oas-token amount sender recipient)
      success 
      (begin 
        (print memo)
        (reduce-spender-amount sender tx-sender amount)
        (ok success)
      )
      error (err error))
  )
)

(define-read-only (get-token-uri)
  (ok (some u"https://openartsource.io/wp-content/uploads/2019/05/OAS_LOGO-long.png"))
)
;; end sip-010

;; read only

(define-read-only (is-admin)
  (or
    (default-to false (map-get? admins tx-sender))
    (default-to false (map-get? admins contract-caller))
  )
)

(define-read-only (get-quote (token-amount uint))
  (let (
      (xrate (var-get stx-token-rate))
      (denom (get denom xrate))
      (num (get num xrate))
      (n (if (is-eq num u0) u1 num))
      (d (if (is-eq denom u0) u1 denom))
      (ab (* token-amount denom))
      (stx (if (is-eq num u0) u0 (/ ab n)))
      (cd (* stx num))
      (token (if (is-eq denom u0) token-amount (/ cd d)))
    )
    {stx: stx, token: token, remain: (if (is-eq denom u0) u0 (mod cd d))} 
  )
)

(define-read-only (get-issued)
  (var-get issued)
)

;; public
(define-public (pause (state bool))
  (begin 
    (asserts! (is-admin) (err u403))
    (var-set paused state)
    (ok true)
  )
)

(define-public (set-rate (new-rate (tuple (num uint) (denom uint))))
  (begin 
    (asserts! (is-admin) (err u403))
    (var-set stx-token-rate new-rate)
    (ok true)
  )
)

(define-public (set-token-uri (new-token-uri (string-utf8 256)))
  (begin 
    (asserts! (is-admin) (err u403))
    (var-set token-uri new-token-uri)
    (ok true)
  )
)

;; add address to admin list
(define-public (set-admin (new-admin principal))
  (begin
    (asserts! (is-admin) (err u403))
    (if (default-to false (map-get? admins new-admin))
      (ok true)
      (begin
        (map-set admins new-admin true)
        (var-set admin-count (+ (var-get admin-count) u1))
        (ok true)
      )
    )
  )
)

;; remove address from admin list
(define-public (remove-admin (old-admin principal) (allow-no-admin bool))
  (begin
    (asserts! (is-admin) (err u403))
    (if (default-to false (map-get? admins old-admin))
      false
      (begin
        (map-delete admins old-admin)
        (var-set admin-count (- (var-get admin-count) u1))
        true
      )
    )
    (asserts! (or allow-no-admin (> (var-get admin-count) u0)) (err u1234))
    (ok true)
  )
)

(define-public (withdraw-remain)
  (let (
    (this-contract (as-contract tx-sender))
    (recipient tx-sender)
    ) 
    (asserts! (is-admin) (err u403))
    (asserts! (<= (ft-get-supply oas-token) (+ init-amount (/ init-amount u20))) (err u1234))
    (as-contract (stx-transfer? (stx-get-balance this-contract) this-contract recipient))
  )
)

(define-public (mint (amount uint))
  (let (
      (transfer-amount (get-quote amount))
      (this-contract (as-contract tx-sender))
      (token (get token transfer-amount))
      (stx (get stx transfer-amount))
    ) 
    (asserts! (not (var-get paused)) (err u1234))
    (asserts! (> token u0) (err u1236))
    (unwrap! (ft-mint? oas-token token tx-sender) (err u1235))
    (var-set issued (+ (var-get issued) token))
    (if (is-eq stx u0)
      (ok true)
      (stx-transfer? (get stx transfer-amount) tx-sender this-contract)
    )
  )
)

(define-public (redeem (amount uint))
  (let (
      (transfer-amount (get-quote amount))
      (redeemer tx-sender)
      (this-contract (as-contract tx-sender))
      (token (get token transfer-amount))
      (stx (get stx transfer-amount))
    ) 
    (asserts! (not (var-get paused)) (err u1234))
    (asserts! (> token u0) (err u1236))
    (unwrap! (ft-burn? oas-token token tx-sender) (err u1235))
    (var-set issued (- (var-get issued) token))
    (if (is-eq stx u0)
      (ok true)
      (as-contract (stx-transfer? (get stx transfer-amount) this-contract redeemer))
    )
  )
)

(define-public (approve (spender principal) (amount uint))
  (if (is-eq spender tx-sender)
      (err u1)
      (begin
        (map-set tokens-spender
                    {owner: tx-sender, spender: spender}
                    amount)
        (ok true)))

)

;; private
;; Gets the approved amount for the spender address
(define-private (is-spender-approved (spender principal) (owner principal) (amount uint))
  (let ((approved-amount
         (default-to u0 (map-get? tokens-spender {owner: owner, spender: spender})))
        )
    (<= amount approved-amount))
)

(define-private (reduce-spender-amount (owner principal) (spender principal) (amount uint))
  (if (is-eq owner spender)
    true
    (let ((approved-amount
         (default-to u0 (map-get? tokens-spender {owner: owner, spender: spender})))
        )
      (if (and (> approved-amount u0) (> approved-amount amount))
        (map-set tokens-spender {owner: owner, spender: spender} (- approved-amount amount))
	      true
      )
      true
    )
  )
)
;; Returns whether the given actor can transfer amount for owner
(define-private (can-transfer (actor principal) (owner principal) (amount uint))
  (or
   (is-eq actor owner)
   (is-spender-approved actor owner amount)
   )
)

;; Initialize the contract
(begin
;; set admin account
  (map-set admins tx-sender true)
  (var-set admin-count u1)
;; Mint Tokens
  (ft-mint? oas-token init-amount tx-sender)
  )


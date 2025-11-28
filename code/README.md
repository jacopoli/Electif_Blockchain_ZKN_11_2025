# Blockchain with Confidential Transactions - README

## Overview

This project implements a **pedagogical blockchain** with **confidential transactions** using a zk-SNARK simulation. It demonstrates how cryptographic proofs can hide sensitive information (balances, amounts) while maintaining blockchain integrity and transaction authenticity.

## Project Structure

### Core Files

#### **`block.py`**

Implements the `Block` class representing a single block in the blockchain.

**Key Responsibilities:**

- Store transactions, timestamp, proof of work, and chain pointers
- Generate block hashes using SHA256
- Implement proof of work mining (difficulty-based)
- Validate block integrity and proofs

**Key Methods:**

- `hash()` - Compute SHA256 hash of the block
- `mine(difficulty)` - Find proof of work by iterating until hash matches difficulty
- `validity()` - Check if block is valid (genesis block or valid PoW + transactions)
- `next(transactions)` - Create new block following current one
- `log()` - Display block details in rich tables

---

#### **`transaction.py`**

Implements the `Transaction` class for confidential transactions.

**Key Responsibilities:**

- Store confidential transaction data (no plain text amounts)
- Sign transactions with ECDSA private keys
- Verify transaction authenticity and zero-knowledge proofs
- Manage state transition hashes

**Key Methods:**

- `sign(sk)` - Sign transaction with private key, compute author hash
- `verify()` - Verify ECDSA signature + zk-SNARK proof
- `hash()` - Compute transaction hash (includes signature)
- `data` property - Return serializable transaction dictionary
- `json_dumps()` - JSON representation for signing

**Attributes:**

- `public_inputs` - Dictionary with state transition hashes:
  - `hash_sender_old` - Hash of sender's previous balance
  - `hash_sender_new` - Hash of sender's new balance
  - `hash_value` - Hash of transfer amount
- `zk_proof` - Zero-knowledge proof of balance knowledge
- `vk` - Sender's public key (hex)
- `author` - Hash of sender's public key (address)
- `signature` - ECDSA signature (hex)
- `date` - Transaction timestamp

---

#### **`blockchain.py`**

Implements the `Blockchain` class managing the entire chain and mempool.

**Key Responsibilities:**

- Maintain chain of blocks and pending transactions (mempool)
- Manage state hashes (balance tracking per address)
- Validate transactions and blocks
- Handle blockchain merging for consensus

**Key Methods:**

- `add_transaction(tx)` - Add transaction to mempool with validation
- `new_block()` - Create new block from mempool transactions
- `extend_chain(block)` - Add validated block and update state
- `validity()` - Check entire chain integrity
- `merge(other)` - Adopt longer valid chain
- `display_content()` - Rich formatted blockchain display
- `log()` - Display chain and mempool

**Key Attributes:**

- `chain` - List of blocks (starts with genesis block)
- `mempool` - Set of pending transactions
- `state_hashes` - Dict mapping `address -> current_balance_hash`

---

#### **`zk_sim.py`** ⭐ Zero-Knowledge SNARK Simulation

The heart of confidential transactions. Implements a pedagogical zk-SNARK system using SHA256.

**What is a zk-SNARK?**

- **Zero-Knowledge**: Prove a statement without revealing the secret
- **Succinct**: Proof is small and fast to verify
- **Non-Interactive**: Doesn't require back-and-forth communication
- **Argument of Knowledge**: Prover knows the secret

**How zk_sim Works:**

**1. Commitment (Hiding)**

```python
commitment = SHA256(secret_value : nonce)
```

- The commitment is publicly stored on blockchain
- The secret stays hidden (you can't reverse SHA256)
- Only the prover knows the pre-image (secret + nonce)

**2. Proof Generation**

```python
proof = zk_sim.prove(secret_value, secret_nonce)
```

Returns a `ZKProof` object containing:

- `secret` - The hidden value
- `nonce` - Random nonce for security
- `commitment` - SHA256 hash (publicly visible)

**3. Verification**

```python
is_valid = zk_sim.verify_zk(public_hash, proof_dict)
```

Verification equation:

```
SHA256(proof.secret : proof.nonce) == public_hash ?
```

- Only verifies the commitment matches
- Never reveals the secret
- Cryptographically secure

**Key Functions:**

- `prove(secret_value, nonce)` - Create proof with commitment
- `verify_zk(public_hash, proof_dict)` - Verify proof validity
- `hash_secret(secret, nonce)` - Compute commitment hash

**Limitations (Pedagogical):**

- Simple SHA256-based (no circuit proofs)
- Security through hashing, not formal ZK
- No range proofs (can't verify balance ≥ 0)
- Sender identifiable (no privacy beyond amounts)

---

#### **`config.py`**

Configuration constants for the blockchain.

**Key Parameters:**

- `default_difficulty` - Proof of work difficulty (zeros at start of hash)
- `blocksize` - Maximum transactions per block

---

#### **`utils.py`**

Utility functions for the project.

**Key Functions:**

- `get_time()` - Get current timestamp
- `hash_string(s)` - SHA256 hash a string

---

#### **`test_confidential.py`**

Complete demonstration of confidential transactions.

**What it demonstrates:**

1. Alice generates ECDSA keypair
2. Creates balance commitment (100 units hidden)
3. Makes first confidential transfer (30 units hidden)
4. Submits to blockchain, gets mined into Block 1
5. Makes second transfer (20 units hidden)
6. Mines Block 2
7. Verifies signatures, proofs, and chain validity
8. Shows privacy summary (what's hidden vs. visible)
9. Displays full blockchain content

**Run with:**

```bash
python test_confidential.py
```

---

## How Confidential Transactions Work

### Transaction Flow

```
1. SETUP
   Alice's Secret Balance: 100 (HIDDEN)
   Nonce: "alice_nonce_12345"

2. CREATE COMMITMENT
   hash_old = SHA256(100 : "alice_nonce_12345") = "003456785cfd735c..."
   ✓ Stored on blockchain (commitment)

3. CREATE TRANSACTION
   Transfer: 30 units
   New Balance: 70 units
   hash_new = SHA256(70 : "alice_nonce_12346") = "7010a4493685cf15..."

4. CREATE PROOF
   proof = zk_sim.prove(100, "alice_nonce_12345")
   Contains: {secret: 100, nonce: "alice_nonce_12345", commitment: "003456..."}

5. SIGN TRANSACTION
   Tx = {
       public_inputs: {
           hash_sender_old: "003456785cfd735c...",  # Public
           hash_sender_new: "7010a4493685cf15...",  # Public
           hash_value: "fb14eadd9a363443..."        # Public (amount hash)
       },
       zk_proof: {secret: 100, nonce: "...", commitment: "003456..."},
       signature: "d051f13f5667e87b...",  # ECDSA signature
       author: "8e2d6d0d30013488..."     # Hash of public key
   }
   Sign with Alice's private key

6. VERIFY BLOCKCHAIN
   - Check ECDSA signature: ✓ Only Alice could sign
   - Check zk-proof: SHA256(100 : "nonce") == hash_old ? ✓ Valid
   - Check state: hash_old == blockchain.state_hashes[Alice] ? ✓ Matches
   - All checks pass → Accept transaction

7. UPDATE STATE
   blockchain.state_hashes[Alice] = "7010a4493685cf15..."
   Next transaction must reference this new hash

8. SECOND TRANSACTION
   Alice transfers 20 more units
   hash_old = "7010a4493685cf15..." (her updated state)
   hash_new = SHA256(50 : "nonce_12347") = "fb8ee54165f4cd7f..."
   ✓ Block 2 validates and updates state
```

### What's Hidden vs. Visible

**HIDDEN:**

- ❌ Alice's balance (100)
- ❌ Transfer amounts (30, 20)
- ❌ New balances (70, 50)
- ❌ Secret nonces

**VISIBLE:**

- ✓ State transition hashes (hash_old → hash_new)
- ✓ Alice's address (derived from public key)
- ✓ ECDSA signatures
- ✓ Transaction hashes
- ✓ Timestamps
- ✓ Proof commitments

### Security Properties

**1. Confidentiality**

- Balances never appear in plaintext
- Only SHA256 commitments visible
- Requires knowledge of secret to generate valid proof

**2. Authenticity**

- ECDSA signatures prevent forgery
- Only Alice can sign (has private key)
- Transaction tampering invalidates signature

**3. Correctness**

- zk-SNARK proofs verify knowledge of pre-image
- Blockchain tracks state transitions
- Invalid proofs rejected

**4. No Double-Spending**

- Each transaction references previous state hash
- Blockchain enforces linear state progression
- Can't reuse old state

---

## Usage Example

```python
from ecdsa import SigningKey
from blockchain import Blockchain
from transaction import Transaction
import zk_sim

# 1. Create blockchain
blockchain = Blockchain()

# 2. Alice generates keys
sk_alice = SigningKey.generate()

# 3. Create secret balance and prove knowledge
secret_balance = 100
nonce = "secret_nonce_123"
proof = zk_sim.prove(secret_balance, nonce)
hash_old = proof.commitment

# 4. Create transaction
new_balance = 70
new_proof = zk_sim.prove(new_balance, "new_nonce_456")
hash_new = new_proof.commitment

tx = Transaction(
    public_inputs={
        "hash_sender_old": hash_old,
        "hash_sender_new": hash_new,
        "hash_value": zk_sim.prove(30, "transfer_nonce").commitment
    }
)
tx.zk_proof = proof.to_dict()
tx.sign(sk_alice)

# 5. Add to blockchain
blockchain.add_transaction(tx)

# 6. Mine block
block = blockchain.new_block()
block.mine()
blockchain.extend_chain(block)

# 7. Display blockchain
blockchain.display_content()
```

---

## File Dependencies

```
test_confidential.py
    └── transaction.py
    └── blockchain.py
    └── zk_sim.py
    │
    blockchain.py
    ├── block.py
    ├── transaction.py
    ├── config.py
    └── zk_sim.py

    transaction.py
    ├── utils.py
    └── zk_sim.py

    block.py
    ├── config.py
    ├── utils.py
    └── transaction.py
```

---

## Key Concepts Explained

### Proof of Work (Mining)

- Find a nonce value such that `SHA256(block)` starts with `difficulty` zeros
- More zeros = harder problem = more computational work
- Prevents spam and secures blockchain

### State Hashes

- Track current balance for each address
- Updated when transaction is confirmed
- New transactions must reference current state
- Prevents replaying old transactions

### Nonces

- Random values used in zk-SNARK proofs
- Different nonces produce different commitments
- Prevents adversary from guessing secrets via brute force

### Commitments

- One-way functions (SHA256)
- Hide the secret value
- Cryptographically binding (can't change secret without changing commitment)

---

## Real-World zk-SNARKs vs. This Implementation

| Feature                     | Real zk-SNARK          | zk_sim.py                     |
| --------------------------- | ---------------------- | ----------------------------- |
| **Circuit Language**        | Circom, R1CS           | None (just hashes)            |
| **Proof Size**              | Small (~288 bytes)     | Large (stores secret + nonce) |
| **Verification**            | Complex pairing math   | Simple hash comparison        |
| **Zero-Knowledge Property** | Formal, proven         | Security through hashing      |
| **Range Proofs**            | Supported              | Not supported                 |
| **Use Cases**               | Production blockchains | Education, understanding      |

**Real zk-SNARK Libraries:**

- **libsnark** - C++ implementation by Eli Ben-Sasson
- **Circom + SnarkJS** - Circuit language + JavaScript verifier
- **ZK-STARK** - Transparent alternative (no trusted setup)
- **Bulletproofs** - Range proofs without trusted setup

---

## Extensions & Improvements

### To make this more realistic:

1. **Add Range Proofs**

   - Prove balance ≥ 0 without revealing value
   - Prevents sending negative amounts

2. **Add Recipient Stealth Addresses**

   - Hide receiver identity
   - Use ephemeral keys

3. **Add Nullifiers**

   - Mark spent commitments
   - Prevent double-spending proofs

4. **Implement Circuit Verification**

   - Define spending rules in circuit
   - Verify complex constraints

5. **Add Merkle Trees**
   - Prove membership without revealing all commitments
   - More efficient for large sets

---

## Running the Project

### Requirements

```powershell
# Create and activate a local virtualenv, then install requirements
python -m venv .venv
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass; .\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip setuptools wheel
python -m pip install -r .\requirements.txt

# Quick check
python .\run_zk_check.py
```

Notes:

- The project prefers `py_ecc` (pure-Python EC library). When `py_ecc` is installed, `zk_sim.py` uses Pedersen commitments
  and Schnorr-style (Fiat–Shamir) proofs based on `bn128` (EC) primitives — this hides values while enabling proof of
  knowledge of committed values.
- If `py_ecc` is NOT installed, `zk_sim.py` falls back to a SHA256-based pedagogical mode so the demo remains runnable.
- `zk_sim` accepts string nonces/values: they are deterministically hashed to integers so you can pass human-friendly
  nonces (e.g. `"alice_nonce_12345"`) and the EC code will work.

### Run Confidential Transaction Demo

```bash
python test_confidential.py
```

### Test Individual Components

```bash
# Test block mining
python block.py

# Test basic transactions
python transaction.py

# Test blockchain
python blockchain.py
```

---

## Summary

This project demonstrates:

- ✅ **Cryptographic Signatures** (ECDSA) for authenticity
- ✅ **Proof of Work** for blockchain security
- ✅ **Zero-Knowledge Proofs** (simplified) for confidentiality
- ✅ **State Management** via hash chains
- ✅ **Transaction Validation** with multiple checks
- ✅ **Consensus** via longest chain rule

The combination of ECDSA + zk-SNARKs creates a blockchain where:

- **You prove you authorized a transaction** (ECDSA signature)
- **You prove you know the pre-image of hashes** (zk-SNARK)
- **Nobody learns your balance or amounts** (confidentiality)
- **The blockchain remains immutable and valid** (integrity)

This is the foundation of privacy-preserving blockchains like **Zcash**, **Monero**, and **Tornado Cash**.

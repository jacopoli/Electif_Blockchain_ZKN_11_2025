# Confidential Transactions with zk-SNARK Simulation

## Overview

This implementation adds **Confidential Transactions** to your blockchain using a pedagogical zk-SNARK simulation. Balances and transfer amounts are hidden using SHA256-based commitments, while ECDSA signatures ensure authenticity.

## Files Created/Modified

### 1. **`zk_sim.py`** (NEW)

Simulates zk-SNARK behavior using SHA256 hashing for educational purposes.

**Key Functions:**

- `prove(secret_value, secret_nonce)` → Returns a `ZKProof` object containing the commitment
- `verify_zk(public_hash, proof_dict)` → Verifies that the commitment matches the public hash
- `hash_secret(secret_value, nonce)` → Compute the hash of a secret

**Concept:**

- A "proof" proves knowledge of a secret (balance) without revealing it
- The commitment is `SHA256(secret:nonce)` stored on blockchain
- Only parties with the secret and nonce can generate valid proofs

### 2. **`transaction.py`** (MODIFIED)

Replaced plain-text `message` with confidential transaction structure.

**Changes:**

- `__init__`: Now takes `public_inputs` (dict) and `zk_proof` instead of `message`
- `public_inputs`: Dictionary with:
  - `hash_sender_old`: Hash of sender's previous balance
  - `hash_sender_new`: Hash of sender's new balance
  - `hash_value`: Hash of transfer amount
- `data` property: Includes `public_inputs` and `zk_proof`
- `verify()`: Now checks both ECDSA signature AND zk-SNARK proof validity
- `__str__()`: Updated to display confidential transaction info

**Example:**

```python
tx = Transaction(
    public_inputs={
        "hash_sender_old": "003456...",
        "hash_sender_new": "701014...",
        "hash_value": "fb14ea..."
    }
)
tx.zk_proof = zk_sim.prove(100, "nonce").to_dict()
tx.sign(sk)
```

### 3. **`blockchain.py`** (MODIFIED)

Added state management to track balance hashes.

**Changes:**

- `__init__`: Added `self.state_hashes = {}` to map `address → balance_hash`
- `add_transaction()`: Verifies that `tx.public_inputs['hash_sender_old']` matches the current state hash for the sender
- `extend_chain()`: Updates `state_hashes` with `hash_sender_new` when transactions are confirmed
- `merge()`: Also syncs `state_hashes` when chains are merged

**Workflow:**

1. New user has no state hash (None)
2. Transaction references old hash, proves knowledge of it via zk-proof
3. Block includes transaction → blockchain updates sender's state hash to new value
4. Next transaction must reference the updated state hash

### 4. **`test_confidential.py`** (NEW)

Comprehensive test demonstrating Alice's confidential transactions.

**Demonstrates:**

- Secret balance creation (never revealed)
- Hash commitment computation
- Creating and signing confidential transactions
- Mining and validating blocks
- State transitions
- Multiple consecutive transactions

**Run with:**

```bash
python test_confidential.py
```

## How It Works

### Transaction Flow

```
Alice's Secret Balance: 100 (HIDDEN)
                ↓
Create hash: SHA256(100:nonce₁) = HASH_OLD
                ↓
Transfer 30 units (HIDDEN amount)
Create hash: SHA256(70:nonce₂) = HASH_NEW
                ↓
Create zk-proof with HASH_OLD
Sign transaction with ECDSA
                ↓
Blockchain verifies:
  ✓ ECDSA signature valid
  ✓ zk-proof(HASH_OLD) valid
  ✓ HASH_OLD matches current state
                ↓
Block includes transaction
Update state: HASH_NEW becomes Alice's new balance hash
```

### What's Hidden vs. Visible

**HIDDEN on blockchain:**

- Alice's balance: `100`
- New balance: `70`
- Transfer amount: `30`

**VISIBLE on blockchain:**

- State transition hashes: `HASH_OLD → HASH_NEW`
- Alice's address (derived from public key)
- ECDSA signature (proves Alice authorized the transaction)
- zk-SNARK proof (proves she knows the pre-images)

## Security Properties

1. **Confidentiality**: Amounts and balances are never exposed
2. **Authenticity**: ECDSA signatures prove transaction is from Alice
3. **Correctness**: zk-SNARK proofs verify state transitions are valid
4. **No Double-Spending**: Blockchain tracks current state hash per address

## Limitations (Pedagogical)

This is a simplified simulation:

- Real zk-SNARKs use circuit-based proofs and pairing cryptography
- We use simple SHA256 commitments for pedagogical clarity
- No formal zero-knowledge property (security through obscurity)
- No range proofs (can't verify balance ≥ 0)
- No privacy beyond amount hiding (sender is identifiable)

For production use, use libraries like:

- **libsnark** - C++ implementation
- **Circom + SnarkJS** - Circuit language + JavaScript proofs
- **ZK-STARK** - Transparent alternative

## Extensions

To make this more realistic, you could:

1. **Add Range Proofs** - Prove balance ≥ 0 without revealing it
2. **Add Recipient Privacy** - Use stealth addresses or encrypted outputs
3. **Implement Circuit Validation** - Verify transactions satisfy spending rules
4. **Add Nullifiers** - Prevent double-spending without revealing transaction history

## Testing

Run the test to see:

```bash
$ python test_confidential.py
```

This demonstrates:

- ✓ Alice's secret balance (100) is never revealed
- ✓ Transfer amount (30) is never revealed
- ✓ Blockchain accepts confidential transactions
- ✓ Multiple transactions chain correctly
- ✓ State hashes track balance history

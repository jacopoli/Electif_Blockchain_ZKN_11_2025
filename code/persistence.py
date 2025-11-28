"""
Persistence module for saving/loading blockchain and authors to/from JSON files.

Authors are serialized as:
  {
    "name": { "sk_hex": "...", "author_hash": "...", "vk_hex": "..." }
  }

Blockchain is serialized as:
  {
    "chain": [ { "transactions": [...], "timestamp": "...", "previous_hash": "...", "proof": ... } ],
    "state_hashes": { "address": "commitment_hash" }
  }
"""

import json
import os
from ecdsa import SigningKey
from blockchain import Blockchain
from block import Block
from transaction import Transaction


AUTHORS_FILE = "authors.json"
BLOCKCHAIN_FILE = "blockchain.json"


def serialize_sk(sk):
    """Serialize a SigningKey to hex string."""
    return sk.to_string().hex()


def deserialize_sk(sk_hex):
    """Deserialize a SigningKey from hex string."""
    return SigningKey.from_string(bytes.fromhex(sk_hex))


def save_authors(authors):
    """Sauvegarde le dictionnaire des auteurs dans un fichier JSON."""
    try:
        with open(AUTHORS_FILE, "w") as f:
            json.dump(authors, f, indent=4)
    except Exception as e:
        print(f"Erreur sauvegarde auteurs: {e}")

def load_authors():
    """Charge les auteurs depuis le JSON."""
    if not os.path.exists(AUTHORS_FILE):
        return {}
    try:
        with open(AUTHORS_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}


def serialize_blockchain(blockchain):
    """Serialize blockchain to JSON-compatible dict.
    
    :param blockchain: Blockchain instance
    :return: Dict with blocks and state_hashes
    """
    blocks_json = []
    for block in blockchain.chain:
        txs_json = []
        for tx in block.transactions:
            txs_json.append(tx.data)
        
        blocks_json.append({
            "transactions": txs_json,
            "timestamp": block.timestamp,
            "previous_hash": block.previous_hash,
            "proof": block.proof,
        })
    
    return {
        "chain": blocks_json,
        "state_hashes": blockchain.state_hashes,
    }


def deserialize_blockchain(bc_json):
    """Deserialize blockchain from JSON dict.
    
    :param bc_json: Dict with blocks and state_hashes
    :return: Blockchain instance
    """
    blockchain = Blockchain()
    
    # Restore state hashes
    blockchain.state_hashes = bc_json.get("state_hashes", {})
    
    # Restore blocks (skip genesis, it's already created)
    for i, block_json in enumerate(bc_json.get("chain", [])):
        if i == 0:
            # Skip genesis (already in blockchain.chain)
            continue
        
        # Reconstruct transactions
        transactions = []
        for tx_data in block_json.get("transactions", []):
            tx = Transaction(
                public_inputs=tx_data.get("public_inputs"),
                date=tx_data.get("date"),
                signature=tx_data.get("signature"),
                vk=tx_data.get("vk"),
                author=tx_data.get("author"),
                zk_proof=tx_data.get("zk_proof"),
            )
            transactions.append(tx)
        
        # Reconstruct block
        block = Block()
        block.index = block_json.get("index", 0)
        block.timestamp = block_json.get("timestamp")
        block.transactions = transactions
        block.previous_hash = block_json.get("previous_hash")
        block.proof = block_json.get("proof", 0)
        
        # Add to chain (bypass validation for simplicity)
        blockchain.chain.append(block)
    
    return blockchain


def save_blockchain(blockchain):
    """Save blockchain to JSON file.
    
    :param blockchain: Blockchain instance
    """
    bc_json = serialize_blockchain(blockchain)
    with open(BLOCKCHAIN_FILE, "w", encoding="utf-8") as f:
        json.dump(bc_json, f, indent=2)


def load_blockchain():
    """Load blockchain from JSON file.
    
    :return: Blockchain instance (or new Blockchain if file doesn't exist)
    """
    if not os.path.exists(BLOCKCHAIN_FILE):
        return Blockchain()
    
    with open(BLOCKCHAIN_FILE, "r", encoding="utf-8") as f:
        bc_json = json.load(f)
    
    try:
        return deserialize_blockchain(bc_json)
    except (ValueError, KeyError, AttributeError) as e:
        print(f"Warning: Could not deserialize blockchain: {e}")
        return Blockchain()

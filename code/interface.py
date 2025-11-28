"""
Streamlit Interface for Confidential Blockchain (ZK-SNARKs)
"""

import streamlit as st
import json
import random
import os
from ecdsa import SigningKey, NIST256p
from blockchain import Blockchain
from transaction import Transaction
import zk_sim as zk  # Utilisation du vrai provider cryptographique
from utils import get_time

# --- GESTION DE LA PERSISTANCE ---
# On essaie d'importer les fonctions de sauvegarde.
# Si le fichier persistence.py n'existe pas, on utilise des fonctions "vides" pour ne pas faire planter l'interface.
try:
    from persistence import load_authors, save_authors, load_blockchain, save_blockchain
except ImportError:
    def load_authors(): return {}
    def save_authors(data): pass
    def load_blockchain(): return Blockchain()
    def save_blockchain(bc): pass

# Configuration de la page Streamlit
st.set_page_config(page_title="ZK Blockchain", layout="wide", page_icon="🔐")

# ============================================================================
# 1. INITIALISATION DE LA MÉMOIRE (SESSION STATE)
# ============================================================================

if "blockchain" not in st.session_state:
    st.session_state.blockchain = load_blockchain()

# Structure des auteurs (Wallet) : 
# name -> {
#    "sk_pem": string, 
#    "vk_hex": string, 
#    "address": string,
#    "private": {"balance": int, "nonce": int}  <-- C'est ici que sont les secrets ZK
# }
if "authors" not in st.session_state:
    st.session_state.authors = load_authors()

if "current_author" not in st.session_state:
    st.session_state.current_author = None

# ============================================================================
# 2. BARRE LATÉRALE (SIDEBAR) - GESTION DU WALLET
# ============================================================================

st.sidebar.title("🔐 ZK Wallet")

# --- A. Création d'un nouveau compte ---
st.sidebar.subheader("Create New Account")
new_author_name = st.sidebar.text_input("User Name", key="new_author_input")
initial_balance = st.sidebar.number_input("Initial Balance (Mint)", min_value=0, value=100)

if st.sidebar.button("Create Account"):
    if new_author_name and new_author_name not in st.session_state.authors:
        # 1. Génération des clés ECDSA (Identité)
        sk = SigningKey.generate(curve=NIST256p)
        vk_hex = sk.verifying_key.to_pem().hex()
        import hashlib
        address = hashlib.sha256(vk_hex.encode()).hexdigest()
        
        # 2. État ZK Initial (Genesis)
        # On génère un nonce aléatoire pour masquer le solde initial
        init_nonce = random.randint(1, 10000000)
        genesis_comm = zk.commit(initial_balance, init_nonce)
        
        # 3. Stockage dans le Wallet (Local)
        st.session_state.authors[new_author_name] = {
            "sk_pem": sk.to_pem().decode(),
            "vk_hex": vk_hex,
            "address": address,
            "private": {
                "balance": initial_balance,
                "nonce": init_nonce
            }
        }
        
        # 4. Injection dans la Blockchain (Simulation de Minting)
        st.session_state.blockchain.state_hashes[address] = genesis_comm
        
        # 5. Sauvegarde sur le disque
        save_authors(st.session_state.authors)
        
        save_blockchain(st.session_state.blockchain) # Décommentez si vous implémentez la sauvegarde complète
        
        st.sidebar.success(f"Account '{new_author_name}' created!")
        st.session_state.current_author = new_author_name
        st.rerun()

# --- B. Sélection du compte actif ---
st.sidebar.markdown("---")
st.sidebar.subheader("Active Wallet")
author_list = list(st.session_state.authors.keys())

if author_list:
    current = st.sidebar.selectbox(
        "Select User",
        author_list,
        index=author_list.index(st.session_state.current_author) if st.session_state.current_author in author_list else 0
    )
    st.session_state.current_author = current
    
    user_data = st.session_state.authors[current]
    st.sidebar.info(f"**Address:** `{user_data['address'][:10]}...`")
    
    # Debug : Voir les secrets (Pour comprendre ce qui se passe)
    with st.sidebar.expander("👁️ View Private Secrets"):
        priv = user_data['private']
        st.write(f"**Real Balance:** {priv['balance']}")
        st.write(f"**Current Nonce:** {priv['nonce']}")
        
        # Vérification de synchro Wallet <-> Blockchain
        on_chain_hash = st.session_state.blockchain.state_hashes.get(user_data['address'])
        my_calc_hash = zk.commit(priv['balance'], priv['nonce'])
        
        if on_chain_hash == my_calc_hash:
            st.markdown("✅ **Synced with Chain**")
        else:
            st.markdown("❌ **Desynchronized!**")
            st.caption("Please mine pending blocks.")
else:
    st.sidebar.warning("No accounts found.")

# --- C. Bouton RESET (Système) ---
st.sidebar.markdown("---")
st.sidebar.subheader("⚙️ System")

if st.sidebar.button("🔴 RESET SYSTEM", type="primary"):
    # 1. Vider la mémoire de l'application
    st.session_state.blockchain = Blockchain()
    st.session_state.authors = {}
    st.session_state.current_author = None
    
    # 2. Mettre à jour les fichiers JSON pour la persistance
    # On sauvegarde un dictionnaire vide pour écraser les anciennes données
    save_authors({})
    
    # On supprime la blockchain si elle existe (ou on la vide)
    if os.path.exists("blockchain.json"):
        os.remove("blockchain.json")
    
    st.sidebar.success("System Reset Complete.")
    st.rerun()


# ============================================================================
# 3. PAGE PRINCIPALE - CRÉATION DE TRANSACTION
# ============================================================================

st.title("Confidential Blockchain Interface")
st.markdown(" Transactions verified via **Zero-Knowledge Proofs**. Amounts are hidden.")

st.subheader("💸 Send Confidential Transaction")

if st.session_state.current_author:
    col1, col2 = st.columns(2)
    with col1:
        amount_to_send = st.number_input("Amount to Transfer", min_value=1, value=10)
    with col2:
        receivers = [u for u in author_list if u != st.session_state.current_author]
        receiver_name = st.selectbox("Receiver", receivers) if receivers else None
    
    if st.button("Submit Transaction"):
        sender_name = st.session_state.current_author
        sender_data = st.session_state.authors[sender_name]
        
        # --- ÉTAPE 0 : VÉRIFICATION DE SYNCHRONISATION ---
        current_chain_hash = st.session_state.blockchain.state_hashes.get(sender_data['address'])
        my_secret_bal = sender_data['private']['balance']
        my_secret_nonce = sender_data['private']['nonce']
        
        # On recalcule notre hash local pour voir s'il matche la blockchain
        my_calc_hash = zk.commit(my_secret_bal, my_secret_nonce)
        
        if current_chain_hash and current_chain_hash != my_calc_hash:
            st.error("⚠️ Wallet desynchronized! You likely have pending transactions.")
            st.warning("👉 Please click '⛏️ Mine Block' below to process pending transactions first.")
        
        elif my_secret_bal < amount_to_send:
            st.error(f"Insufficient funds! You have {my_secret_bal}.")
            
        else:
            try:
                # --- ÉTAPE 1 : PRÉPARATION DES SECRETS ---
                # 1. Expéditeur : Solde - Montant
                new_balance_sender = my_secret_bal - amount_to_send
                new_nonce_sender = random.randint(1, 100000000)
                
                # 2. Nonce de transfert (partagé avec le destinataire)
                transfer_nonce = random.randint(1, 100000000)
                
                # --- ÉTAPE 2 : CRYPTOGRAPHIE ZK ---
                # 1. Commitments (Données publiques sur la blockchain)
                h_old = current_chain_hash
                h_new = zk.commit(new_balance_sender, new_nonce_sender)
                h_val = zk.commit(amount_to_send, transfer_nonce)
                
                # 2. Preuve (Prouver qu'on connait le secret de h_old)
                proof = zk.prove(my_secret_bal, my_secret_nonce)
                
                # --- ÉTAPE 3 : CRÉATION DE L'OBJET TRANSACTION ---
                sk = SigningKey.from_pem(sender_data['sk_pem'].encode())
                
                tx = Transaction(
                    public_inputs={
                        "h_old": h_old,
                        "h_new": h_new,
                        "h_val": h_val
                    },
                    zk_proof=proof
                )
                
                # Ajout du destinataire
                if receiver_name:
                     tx.receiver = st.session_state.authors[receiver_name]['address']

                tx.sign(sk)
                
                # --- ÉTAPE 4 : ENVOI À LA BLOCKCHAIN ---
                if st.session_state.blockchain.add_transaction(tx):
                    st.success("Transaction accepted in Mempool!")
                    
                    # --- ÉTAPE 5 : MISE À JOUR DES WALLETS (LOCAUX) ---
                    
                    # A. Update Sender (On remplace ses secrets)
                    st.session_state.authors[sender_name]['private']['balance'] = new_balance_sender
                    st.session_state.authors[sender_name]['private']['nonce'] = new_nonce_sender
                    
                    # B. Update Receiver (On ADDITIONNE ses secrets - Homomorphisme)
                    if receiver_name:
                         rec_data = st.session_state.authors[receiver_name]
                         
                         # Initialisation si le receiver n'a jamais rien reçu
                         if 'private' not in rec_data: 
                             rec_data['private'] = {'balance': 0, 'nonce': 0}
                         
                         # Logique additive : Balance + Montant
                         rec_data['private']['balance'] += amount_to_send
                         # Logique additive : Nonce + NonceTransfert (C(A)+C(B) = C(A+B))
                         rec_data['private']['nonce'] += transfer_nonce
                    
                    # Sauvegarde immédiate pour la persistance !
                    save_authors(st.session_state.authors)
                    
                    st.rerun()
                else:
                    st.error("Transaction rejected by Blockchain (Invalid Proof or State mismatch).")
            
            except Exception as e:
                st.error(f"Error: {e}")
                # Debugging info
                import traceback
                st.text(traceback.format_exc())

# ============================================================================
# 4. DASHBOARD - BLOCKCHAIN & MEMPOOL
# ============================================================================

col_chain, col_pool = st.columns([2, 1])

with col_chain:
    st.subheader("⛓️ Blockchain")
    
    # Bouton de Minage
    if st.button("⛏️ Mine Block"):
        if not st.session_state.blockchain.mempool:
            st.warning("Mempool is empty.")
        else:
            block = st.session_state.blockchain.new_block()
            block.mine()
            st.session_state.blockchain.extend_chain(block)
            
            # Sauvegarde de la blockchain (si implémenté)
            save_blockchain(st.session_state.blockchain)
            
            st.success("Block Mined!")
            st.rerun()

    # Affichage des blocs
    for i, block in enumerate(reversed(st.session_state.blockchain.chain)):
        with st.expander(f"Block #{block.index} - {block.hash()[:10]}...", expanded=(i==0)):
            st.write(f"**Tx Count:** {len(block.transactions)}")
            if block.transactions:
                t_data = []
                for tx in block.transactions:
                    t_data.append({
                        "Author": tx.author[:8]+"...",
                        "New State (Hash)": str(tx.public_inputs.get('h_new'))[:10]+"...",
                        "Amount (Hash)": str(tx.public_inputs.get('h_val'))[:10]+"..."
                    })
                st.dataframe(t_data)

with col_pool:
    st.subheader("📥 Mempool")
    if st.session_state.blockchain.mempool:
        for tx in st.session_state.blockchain.mempool:
            st.info(f"Tx from `{tx.author[:8]}...`\nProof Verified ✅")
    else:
        st.write("Empty")

# ============================================================================
# 5. ÉTAT GLOBAL (VUE PUBLIQUE)
# ============================================================================
st.markdown("---")
st.subheader("🌍 Ledger State (Public View)")

if st.session_state.blockchain.state_hashes:
    state_rows = []
    for addr, h in st.session_state.blockchain.state_hashes.items():
        # On essaie de retrouver le nom pour l'affichage (facultatif)
        name = "Unknown"
        for n, d in st.session_state.authors.items():
            if d['address'] == addr: name = n
            
        state_rows.append({
            "User": name,
            "Public Commitment (Hash)": h[:50]+"..." 
        })
    st.table(state_rows)
else:
    st.write("No accounts on chain.")
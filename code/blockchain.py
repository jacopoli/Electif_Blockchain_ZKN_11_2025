"""
This module contains the class Blockchain. A blockchain is a list of blocks and a mempool.
It manages the state of confidential balances using commitments (hashes).
"""
import random
import config
from block import Block, InvalidBlock
from transaction import Transaction
import zk_sim as zk # Nécessaire pour les tests

class Blockchain(object):
    def __init__(self):
        self.chain = [Block()] # List of blocks
        self.mempool = set()   # Set of transactions
        self.state_hashes = {} # Mapping address (author) -> last_known_balance_commitment

    @property
    def last_block(self):
        return self.chain[-1]

    def add_transaction(self, transaction):
        """
        Add a new transaction to the mempool. Return True if the transaction is valid.
        
        For confidential transactions:
        - Verify the transaction signature and zk-proof
        - Verify that the sender's old balance hash matches the current blockchain state
        """
        # 1. Vérification cryptographique pure (Signature + ZK Proof mathématique)
        if transaction in self.mempool:
            return False
            
        if not transaction.verify():
            print(f"Refus Tx {transaction.hash()[:8]}... : Signature ou Preuve invalide.")
            return False
        
        # 2. Vérification contextuelle (Double dépense / Cohérence d'état)
        author = transaction.author
        
        # On vérifie si l'input "h_old" déclaré correspond à ce que la blockchain connait
        if author is not None and "h_old" in transaction.public_inputs:
            expected_hash = self.state_hashes.get(author)
            actual_hash = transaction.public_inputs.get("h_old")
            
            # Si l'utilisateur a déjà un historique, le hash DOIT correspondre
            if expected_hash is not None and expected_hash != actual_hash:
                print(f"Refus Tx: Hash solde incohérent. Attendu: {expected_hash[:10]}...")
                return False
        
        self.mempool.add(transaction)
        return True
    
    def new_block(self, block=None):
        """
        Create a new block from transactions chosen in the mempool.
        """
        if block is None:
            block = self.last_block
        
        # Select transactions for the new block
        # Note: sorted() utilise transaction.__lt__ (basé sur la date)
        num_transactions = min(config.blocksize, len(self.mempool))
        selected_transactions = random.sample(sorted(self.mempool), num_transactions)
        
        new_block = block.next(selected_transactions)
        return new_block

    def extend_chain(self, block):
        """
        Add a new block to the chain if it is valid.
        Update the state_hashes with the new balance commitments.
        """
        if not block.validity():
            raise InvalidBlock("The block is not valid")
        if block.index != self.last_block.index + 1:
            raise InvalidBlock("The block index is not valid")
        if block.previous_hash != self.last_block.hash():
            raise InvalidBlock("The previous hash is not valid")
        
        self.chain.append(block)
        
        for tx in block.transactions:
            # 1. Mise à jour de l'EXPÉDITEUR (Lui, on remplace car c'est un "Reste à vivre")
            if tx.author and "h_new" in tx.public_inputs:
                self.state_hashes[tx.author] = tx.public_inputs["h_new"]
            
            # 2. Mise à jour du DESTINATAIRE (Lui, on ADDITIONNE)
            if hasattr(tx, 'receiver') and tx.receiver and "h_val" in tx.public_inputs:
                receiver_addr = tx.receiver
                amount_commitment = tx.public_inputs["h_val"]
                
                # Vérifier si le destinataire a déjà un solde
                if receiver_addr in self.state_hashes:
                    current_commitment = self.state_hashes[receiver_addr]
                    
                    # MAGIE HOMOMORPHE : On additionne les points cryptographiques !
                    # Hash(AncienSolde) + Hash(MontantReçu) = Hash(NouveauTotal)
                    new_total_commitment = zk.add_commitments(current_commitment, amount_commitment)
                    
                    self.state_hashes[receiver_addr] = new_total_commitment
                else:
                    # Premier versement : on initialise simplement
                    self.state_hashes[receiver_addr] = amount_commitment
        
        # Nettoyage de la mempool
        for transaction in block.transactions:
            if transaction in self.mempool:
                self.mempool.remove(transaction)

    def validity(self):
        """Check the validity of the chain."""
        if self.chain[0].index != 0 or self.chain[0].previous_hash != "0" * 64:
            return False

        seen_transactions = set()

        for i in range(1, len(self.chain)):
            block = self.chain[i]
            previous_block = self.chain[i - 1]

            if not block.validity():
                return False

            if block.previous_hash != previous_block.hash():
                return False

            for transaction in block.transactions:
                if transaction in seen_transactions:
                    return False
                seen_transactions.add(transaction)

        return True

    def merge(self, other):
        """Merge logic."""
        if len(other.chain) > len(self.chain) and other.validity():
            self.chain = other.chain
            self.state_hashes = other.state_hashes.copy()
            
            # Rebuild mempool
            all_transactions = set()
            for block in self.chain:
                for transaction in block.transactions:
                    all_transactions.add(transaction)
            self.mempool = {t for t in self.mempool if t not in all_transactions}

    def __str__(self):
        return f"Blockchain: {len(self.chain)} blocks, {len(self.mempool)} pending txs, {len(self.state_hashes)} accounts."

    def __len__(self):
        return len(self.chain)

    def display_content(self):
        """
        Affiche le contenu avec Rich (comme dans votre exemple).
        J'ai adapté les clés pour utiliser h_old/h_new.
        """
        from rich.console import Console
        from rich.table import Table
        from rich.panel import Panel

        console = Console()
        console.print(Panel(f"[bold cyan]BLOCKCHAIN CONFIDENTIELLE (ZK)[/bold cyan]", expand=False))
        
        # State Hashes
        if self.state_hashes:
            state_table = Table(title="État des Comptes (Hashs uniquement)")
            state_table.add_column("Adresse", style="cyan")
            state_table.add_column("Commitment Solde Actuel", style="magenta")
            for address, hash_val in self.state_hashes.items():
                state_table.add_row(f"{address[:10]}...", f"{hash_val[:20]}...")
            console.print(state_table)

        # Blocks
        for block in self.chain:
            console.print(f"\n[bold]Block #{block.index}[/bold] (Tx: {len(block.transactions)})")
            if block.transactions:
                tx_table = Table(show_header=True)
                tx_table.add_column("Tx Hash", style="cyan")
                tx_table.add_column("Old Comm", style="yellow")
                tx_table.add_column("New Comm", style="green")
                
                for tx in block.transactions:
                    h_old = tx.public_inputs.get("h_old", "N/A")
                    h_new = tx.public_inputs.get("h_new", "N/A")
                    tx_table.add_row(tx.hash()[:8], str(h_old)[:10], str(h_new)[:10])
                console.print(tx_table)


# --- NOUVEAUX TESTS ADAPTÉS AU ZK ---

def generate_valid_tx(sk, secret_val, nonce):
    """Helper pour créer une Tx valide ZK pour les tests"""
    # 1. Calcul du commitment (ce que la blockchain va voir)
    comm_old = zk.commit(secret_val, nonce)
    
    # 2. Preuve
    proof = zk.prove(secret_val, nonce)
    
    # 3. Création Tx
    inputs = {
        "h_old": comm_old,
        "h_new": zk.commit(secret_val - 10, nonce + 1), # Simulation envoi
        "h_val": zk.commit(10, nonce + 2)
    }
    t = Transaction(public_inputs=inputs, zk_proof=proof)
    t.sign(sk)
    return t

def simple_test():
    print("\n--- SIMPLE TEST (ZK) ---")
    from ecdsa import SigningKey, NIST384p
    
    bc = Blockchain()
    sk = SigningKey.generate(curve=NIST384p)
    
    # On crée 5 transactions valides
    print("Génération de 5 transactions ZK valides...")
    for i in range(5):
        # Chaque tx utilise un nonce différent pour avoir des hashs uniques
        t = generate_valid_tx(sk, 100, i + 1000)
        added = bc.add_transaction(t)
        if not added:
            print(f"Erreur ajout tx {i}")

    print(f"Mempool size: {len(bc.mempool)}")
    
    # Minage
    block = bc.new_block()
    block.mine()
    bc.extend_chain(block)
    
    bc.display_content()

def merge_test():
    print("\n--- MERGE TEST (ZK) ---")
    from ecdsa import SigningKey, NIST384p
    
    bc1 = Blockchain()
    bc2 = Blockchain()
    sk = SigningKey.generate(curve=NIST384p)
    
    # On peuple BC1
    t1 = generate_valid_tx(sk, 50, 111)
    bc1.add_transaction(t1)
    b1 = bc1.new_block()
    b1.mine()
    bc1.extend_chain(b1)
    
    # On peuple BC2 (plus longue)
    t2 = generate_valid_tx(sk, 60, 222)
    bc2.add_transaction(t2)
    b2 = bc2.new_block()
    b2.mine()
    bc2.extend_chain(b2)
    
    t3 = generate_valid_tx(sk, 70, 333)
    bc2.add_transaction(t3)
    b3 = bc2.new_block()
    b3.mine()
    bc2.extend_chain(b3)
    
    print(f"BC1 longueur: {len(bc1)}")
    print(f"BC2 longueur: {len(bc2)}")
    
    # Merge
    print("Fusion de BC2 dans BC1...")
    bc1.merge(bc2)
    
    print(f"BC1 nouvelle longueur: {len(bc1)}")
    if len(bc1) == 3:
        print("SUCCÈS: Merge réussi.")
    else:
        print("ÉCHEC: Merge raté.")

if __name__ == '__main__':
    simple_test()
    merge_test()
"""
Test script demonstrating confidential transactions with ZK-SNARKs (Pedersen Commitments).
"""

from ecdsa import SigningKey, NIST256p
from transaction import Transaction
from blockchain import Blockchain
import hashlib

# --- CORRECTION ICI : On importe le provider réel (py_ecc) ---
import zk_sim as zk 

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

console = Console()

def print_section(title):
    console.print(Panel(f"[bold cyan]{title}[/bold cyan]", expand=False))

def print_step(step_num, description):
    console.print(f"\n[bold yellow]Step {step_num}:[/bold yellow] {description}")

def test_alice_confidential_transaction():
    """
    Simulate Alice with a secret balance making multiple confidential transactions.
    """
    print_section("CONFIDENTIAL TRANSACTIONS - Alice's Hidden Balance")
    
    # ========== SETUP ==========
    print_step(1, "Alice generates her ECDSA keypair")
    sk_alice = SigningKey.generate(curve=NIST256p)
    # Calcul de l'adresse (hash de la clé publique) pour pré-initialiser la blockchain
    vk_hex = sk_alice.verifying_key.to_pem().hex()
    alice_address = hashlib.sha256(vk_hex.encode()).hexdigest()
    
    console.print(f"    ✓ Private key generated")
    console.print(f"    ✓ Address: {alice_address[:16]}...")
    
    blockchain = Blockchain()

    # --- INITIALISATION FORCÉE (Simulation Genesis) ---
    # Alice reçoit 100 au début des temps.
    genesis_balance = 100
    genesis_nonce = 12345
    # On utilise zk.commit (Pedersen)
    genesis_comm = zk.commit(genesis_balance, genesis_nonce)
    
    # On injecte cet état dans la blockchain
    blockchain.state_hashes[alice_address] = genesis_comm
    console.print(f"    ✓ [Genesis] Alice receives 100 (Commitment: {genesis_comm[:10]}...)")


    # ========== TRANSACTION 1 ==========
    print_step(2, "Transaction 1: Alice sends 30 (Hidden)")
    
    # 1. Données Secrètes
    old_balance = 100
    old_nonce = 12345 # Doit correspondre à ce qui est sur la blockchain !
    
    amount_to_send = 60
    amount_nonce = 555
    
    new_balance = old_balance - amount_to_send # 40
    new_nonce = 67890 # Nouveau sel aléatoire pour le nouveau solde
    
    info_table = Table(show_header=False, box=None)
    info_table.add_row("Secret Balance:", f"[yellow]{old_balance}[/yellow]")
    info_table.add_row("Secret Transfer:", f"[red]{amount_to_send}[/red]")
    info_table.add_row("New Balance:", f"[green]{new_balance}[/green]")
    console.print(info_table)
    
    # 2. Calcul des Inputs Publics (Commitments)
    comm_old = genesis_comm
    comm_new = zk.commit(new_balance, new_nonce)
    comm_val = zk.commit(amount_to_send, amount_nonce)
    
    # 3. Génération de la Preuve ZK
    # Alice prouve qu'elle connait le secret (100) du hash comm_old
    proof_tx1 = zk.prove(old_balance, old_nonce)
    
    tx1_info = Table(show_header=False, box=None)
    tx1_info.add_row("Old Hash (Public):", f"[cyan]{comm_old[:15]}...[/cyan]")
    tx1_info.add_row("New Hash (Public):", f"[magenta]{comm_new[:15]}...[/magenta]")
    tx1_info.add_row("Proof generated:", "[green]YES[/green]")
    console.print(tx1_info)
    
    # 4. Création et Signature
    tx1 = Transaction(
        public_inputs={
            "h_old": comm_old,
            "h_new": comm_new,
            "h_val": comm_val
        },
        zk_proof=proof_tx1
    )
    # Si vous avez ajouté le paramètre 'receiver' dans transaction.py, ajoutez-le ici :
    # tx1.receiver = "hash_adresse_de_bob"
    
    tx1.sign(sk_alice)
    console.print(f"    ✓ Transaction signed (Author: {tx1.author[:8]}...)")
    
    # ========== BLOCKCHAIN PROCESS 1 ==========
    print_step(3, "Submit Tx1 to blockchain")
    
    added1 = blockchain.add_transaction(tx1)
    if added1:
        console.print(f"    ✓ Tx1 accepted in mempool")
    else:
        console.print(f"    ❌ Tx1 rejected", style="bold red")
        return # Arrêt si échec

    block1 = blockchain.new_block()
    block1.mine()
    blockchain.extend_chain(block1)
    console.print(f"    ✓ Block #1 mined & extended")
    
    
    # ========== TRANSACTION 2 (Chaînage) ==========
    print_step(4, "Transaction 2: Alice sends 20 (Chained)")
    
    # Alice utilise le résultat de la Tx1
    previous_balance = new_balance # 40
    previous_nonce = 67890 # C'est le 'new_nonce' de la Tx1 !
    
    amount_2 = 20
    amount_nonce_2 = 999
    
    final_balance = previous_balance - amount_2 # 50
    final_nonce = 11111
    
    # Inputs Publics
    comm_old_2 = comm_new # Le hash actuel sur la blockchain
    comm_new_2 = zk.commit(final_balance, final_nonce)
    comm_val_2 = zk.commit(amount_2, amount_nonce_2)
    
    # Preuve : Alice prouve qu'elle connait le secret de comm_new (70)
    proof_tx2 = zk.prove(previous_balance, previous_nonce)
    
    tx2 = Transaction(
        public_inputs={
            "h_old": comm_old_2,
            "h_new": comm_new_2,
            "h_val": comm_val_2
        },
        zk_proof=proof_tx2
    )
    tx2.sign(sk_alice)
    
    added2 = blockchain.add_transaction(tx2)
    if added2:
        console.print(f"    ✓ Tx2 accepted (Chaining successful)")
    else:
        console.print(f"    ❌ Tx2 rejected (Chaining failed)", style="bold red")
        return

    block2 = blockchain.new_block()
    block2.mine()
    blockchain.extend_chain(block2)
    
    
    # ========== VERIFICATION ==========
    print_step(5, "Final State Verification")
    
    verify_table = Table(show_header=False, box=None)
    verify_table.add_row("Blockchain valid:", f"[green]{blockchain.validity()}[/green]")
    verify_table.add_row("Alice's Final Hash:", f"[magenta]{blockchain.state_hashes[alice_address][:15]}...[/magenta]")
    console.print(verify_table)
    
    # ========== DETAILED VIEW ==========
    print_section("BLOCKCHAIN CONTENT")
    blockchain.display_content()
    
    print_section("✅ TEST COMPLETE")

if __name__ == "__main__":
    test_alice_confidential_transaction()
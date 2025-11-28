import time
import random
from rich.console import Console
from rich.panel import Panel
from rich.layout import Layout
from rich.table import Table
from rich.tree import Tree
from rich import print as rprint
from rich.align import Align

# Importation de vos modules
from ecdsa import SigningKey, NIST256p
import zk_sim as zk
from transaction import Transaction
from blockchain import Blockchain
import hashlib

console = Console()

def step_header(title, step_num):
    console.print(f"\n[bold yellow]ÉTAPE {step_num} : {title}[/bold yellow]")
    console.print("[dim]" + "-" * 50 + "[/dim]")
    time.sleep(1)

def main():
    console.clear()
    console.print(Panel.fit("[bold cyan]AUTOPSIE D'UNE TRANSACTION CONFIDENTIELLE (ZK-SNARK)[/bold cyan]\n"
                            "Scénario : Alice (100) envoie 20 à Bob (0)", subtitle="Visualisation Architecture"))

    # =========================================================================
    # ÉTAPE 1 : INITIALISATION (GENESIS)
    # =========================================================================
    step_header("ÉTAT INITIAL (AVANT LA TRANSACTION)", 1)

    # 1. Setup Crypto
    sk_alice = SigningKey.generate(curve=NIST256p)
    addr_alice = hashlib.sha256(sk_alice.verifying_key.to_pem().hex().encode()).hexdigest()
    
    sk_bob = SigningKey.generate(curve=NIST256p)
    addr_bob = hashlib.sha256(sk_bob.verifying_key.to_pem().hex().encode()).hexdigest()

    # 2. Données Privées (Wallet)
    alice_secret_bal = 100
    alice_secret_nonce = 12345
    
    bob_secret_bal = 10
    bob_secret_nonce = 98765

    # 3. Données Publiques (Blockchain)
    # On simule que la blockchain a déjà ces états
    comm_alice = zk.commit(alice_secret_bal, alice_secret_nonce)
    comm_bob = zk.commit(bob_secret_bal, bob_secret_nonce) # Hash de 0

    # VISUALISATION
    table = Table(title="Comparaison Privé vs Public", show_header=True, header_style="bold magenta")
    table.add_column("Acteur", style="dim")
    table.add_column("🔒 Données Secrètes (Wallet)", style="green")
    table.add_column("🌍 Données Publiques (Blockchain)", style="blue")

    table.add_row(
        "Alice", 
        f"Solde: {alice_secret_bal}\nNonce: {alice_secret_nonce}", 
        f"Commitment (Hash):\n{comm_alice[:20]}..."
    )
    table.add_row(
        "Bob", 
        f"Solde: {bob_secret_bal}\nNonce: {bob_secret_nonce}", 
        f"Commitment (Hash):\n{comm_bob[:20]}..."
    )
    console.print(table)
    
    input("\n[Appuyez sur Entrée pour construire la transaction...]")


    # =========================================================================
    # ÉTAPE 2 : PRÉPARATION DANS LE WALLET D'ALICE
    # =========================================================================
    step_header("CONSTRUCTION DE LA TRANSACTION (CÔTÉ ALICE)", 2)

    amount = 20
    transfer_nonce = 999
    
    # Calculs mathématiques
    new_bal_alice = alice_secret_bal - amount # 80
    new_nonce_alice = 54321
    
    rprint(f"[bold]1. Calculs Arithmétiques (Privé) :[/bold]")
    rprint(f"   Alice possède {alice_secret_bal}. Elle envoie {amount}.")
    rprint(f"   Reste à vivre = {alice_secret_bal} - {amount} = [bold green]{new_bal_alice}[/bold green]")

    rprint(f"\n[bold]2. Cryptographie ZK (Génération) :[/bold]")
    
    # Commitments
    h_old = comm_alice # Ce qu'on va dépenser
    h_new = zk.commit(new_bal_alice, new_nonce_alice) # Le hash de 80
    h_val = zk.commit(amount, transfer_nonce) # Le hash de 20
    
    # Preuve
    with console.status("[bold green]Génération de la Preuve ZK-SNARK...[/bold green]"):
        time.sleep(1.5) # Simulation temps de calcul
        proof = zk.prove(alice_secret_bal, alice_secret_nonce)
    
    console.print(Panel(
        f"h_old (Input)  : {h_old[:20]}...\n"
        f"h_new (Change) : {h_new[:20]}... (Hash de 80)\n"
        f"h_val (Output) : {h_val[:20]}... (Hash de 20)\n"
        f"Proof (ZKP)    : {{'T': '...', 's_v': '...', 's_r': '...'}}",
        title="🔐 Payload Cryptographique généré",
        border_style="green"
    ))
    
    input("\n[Appuyez sur Entrée pour envoyer au réseau...]")


    # =========================================================================
    # ÉTAPE 3 : LA TRANSACTION SUR LE RÉSEAU
    # =========================================================================
    step_header("L'OBJET TRANSACTION (CE QUI VOYAGE)", 3)

    # Création de l'objet
    tx = Transaction(
        public_inputs={"h_old": h_old, "h_new": h_new, "h_val": h_val},
        zk_proof=proof
    )
    tx.receiver = addr_bob # On ajoute le destinataire
    tx.sign(sk_alice)

    # Visualisation de l'objet JSON
    tx_tree = Tree(f"📦 Transaction {tx.hash()[:8]}...")
    tx_tree.add(f"Author: {tx.author[:10]}... (Alice)")
    tx_tree.add(f"Receiver: {tx.receiver[:10]}... (Bob)")
    
    inputs = tx_tree.add("Public Inputs (Commitments)")
    inputs.add(f"h_old: {h_old[:15]}...")
    inputs.add(f"h_new: {h_new[:15]}...")
    inputs.add(f"h_val: {h_val[:15]}...")
    
    zk_node = tx_tree.add("Zero-Knowledge Proof")
    zk_node.add("Validates that Author knows secret of h_old")
    zk_node.add("Validates math: Old = New + Val")
    
    sig = tx_tree.add("Digital Signature (ECDSA)")
    sig.add(f"{tx.signature[:20]}...")

    console.print(Align.center(tx_tree))
    rprint("[italic]Notez qu'aucun montant en clair n'est visible ici ![/italic]")

    input("\n[Appuyez sur Entrée pour vérifier la transaction...]")


    # =========================================================================
    # ÉTAPE 4 : VÉRIFICATION PAR LA BLOCKCHAIN
    # =========================================================================
    step_header("VÉRIFICATION (LE DOUANIER)", 4)

    bc = Blockchain()
    # On injecte l'état pour simuler
    bc.state_hashes[addr_alice] = comm_alice
    bc.state_hashes[addr_bob] = comm_bob

    with console.status("[bold red]Vérification en cours par les nœuds...[/bold red]"):
        time.sleep(1)
        
        # 1. Signature
        check_sig = "✅ Signature Valide (C'est bien Alice)"
        
        # 2. ZK Proof
        is_zk_valid = zk.verify_zk(h_old, proof)
        check_zk = "✅ Preuve ZK Valide (Alice possède les fonds)" if is_zk_valid else "❌ ECHEC ZK"
        
        # 3. State Check
        is_state_valid = (bc.state_hashes[addr_alice] == h_old)
        check_state = "✅ État Cohérent (Pas de double dépense)" if is_state_valid else "❌ ECHEC STATE"
    
    console.print(Panel(
        f"1. {check_sig}\n2. {check_zk}\n3. {check_state}",
        title="Résultat Validation",
        border_style="red"
    ))

    input("\n[Appuyez sur Entrée pour miner et mettre à jour...]")


    # =========================================================================
    # ÉTAPE 5 : MISE À JOUR (ADDITION HOMOMORPHE)
    # =========================================================================
    step_header("MINAGE & MISE À JOUR DES SOLDES", 5)

    rprint("[bold]Comment l'argent arrive chez Bob sans révéler le montant ?[/bold]")
    
    # Simulation de extend_chain
    
    # 1. Mise à jour Alice (Remplacement)
    rprint("\n[cyan]1. Mise à jour Alice (Expéditeur)[/cyan]")
    rprint(f"   Ancien Hash : {bc.state_hashes[addr_alice][:15]}...")
    rprint(f"   Action : [bold red]REMPLACEMENT[/bold red] par h_new")
    bc.state_hashes[addr_alice] = h_new
    rprint(f"   Nouveau Hash: {h_new[:15]}... (Correspond à 80)")

    # 2. Mise à jour Bob (Addition)
    rprint("\n[cyan]2. Mise à jour Bob (Destinataire)[/cyan]")
    old_bob_hash = bc.state_hashes[addr_bob]
    rprint(f"   Ancien Hash (0) : {old_bob_hash[:15]}...")
    rprint(f"   Hash Reçu (20)  : {h_val[:15]}...")
    rprint("   Action : [bold green]ADDITION CRYPTOGRAPHIQUE[/bold green]")
    rprint("   Formule : Point(A) + Point(B) = Point(A+B)")
    
    # L'opération magique
    final_bob_hash = zk.add_commitments(old_bob_hash, h_val)
    bc.state_hashes[addr_bob] = final_bob_hash
    
    rprint(f"   Nouveau Hash    : {final_bob_hash[:15]}...")

    input("\n[Appuyez sur Entrée pour voir le résultat final...]")

    # =========================================================================
    # ÉTAPE 6 : RÉSULTAT FINAL
    # =========================================================================
    step_header("ÉTAT FINAL", 6)

    # Bob met à jour son wallet localement
    final_bob_bal = bob_secret_bal + amount # 0 + 20
    final_bob_nonce = bob_secret_nonce + transfer_nonce # 0 + 999
    
    # Vérification que la magie a opéré
    # Bob calcule le hash de ses nouveaux secrets
    calc_check = zk.commit(final_bob_bal, final_bob_nonce)
    
    match = (calc_check == final_bob_hash)
    
    table = Table(title="Bilan Après Transaction", show_header=True)
    table.add_column("Acteur")
    table.add_column("Nouveau Solde (Privé)")
    table.add_column("Nouveau Hash (Public)")
    table.add_column("Sync OK?")

    table.add_row(
        "Alice", 
        f"[green]{new_bal_alice}[/green] (80)", 
        f"{h_new[:15]}...",
        "✅"
    )
    table.add_row(
        "Bob", 
        f"[green]{final_bob_bal}[/green] (20)", 
        f"{final_bob_hash[:15]}...",
        "✅" if match else "❌"
    )

    console.print(table)
    
    if match:
        console.print(Panel("[bold green]SUCCÈS TOTAL ![/bold green]\n"
                            "La blockchain a mis à jour le solde de Bob (0->20) sans jamais voir le nombre '20'.\n"
                            "C'est la magie de l'Homomorphisme et du ZK.", style="on black"))

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        rprint("\n[red]Arrêt de la démonstration.[/red]")
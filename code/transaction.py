"""
This module defines a transaction class. A transaction is a confidential transaction signed by a private key.
The signature can be verified with the public key.
"""

import utils
import json
import hashlib
from ecdsa import VerifyingKey, BadSignatureError
from rich.console import Console
from rich.table import Table

# IMPORTANT : On utilise le provider py_ecc qu'on a créé
import zk_sim as zk

class IncompleteTransaction(Exception):
    pass

class Transaction(object):
    def __init__(self,receiver=None, public_inputs=None, date=None, signature=None, vk=None, author=None, zk_proof=None):
        """
        Create a confidential transaction.
        
        :param public_inputs: Dictionary with keys {'h_old', 'h_new', 'h_val'}
                              (Mapped from sender_old, sender_new, value)
        :param zk_proof: The Zero-knowledge proof dict
        """
        # On s'assure que public_inputs a les bonnes clés attendues par le système
        self.receiver = receiver
        self.public_inputs = public_inputs if public_inputs is not None else {}
        self.date = utils.get_time() if date is None else date
        self.signature = signature
        self.vk = vk
        self.author = author
        self.zk_proof = zk_proof

    @property
    def data(self):
        """
        Propriété utilisée par block.py pour sérialiser la transaction.
        Retourne un dictionnaire complet de la transaction.
        """
        return {
            "receiver": self.receiver,
            "public_inputs": self.public_inputs,
            "date": self.date,
            "signature": self.signature,
            "vk": self.vk,
            "author": self.author,
            "zk_proof": self.zk_proof
        }

    def get_data_to_sign(self):
        """
        Helper to get exactly the data that needs to be signed.
        Must include the proof to prevent malleability.
        """
        d = {
            "public_inputs": self.public_inputs,
            "date": self.date,
            "author": self.author,
            "vk": self.vk,
            "zk_proof": self.zk_proof 
        }
        # On trie les clés pour garantir que le string est toujours identique
        return json.dumps(d, sort_keys=True)

    @staticmethod
    def author_from_sk(sk):
        vk_hex = sk.verifying_key.to_pem().hex()
        return hashlib.sha256(vk_hex.encode()).hexdigest()

    def sign(self, sk):
        """
        Sign a transaction. 
        WARNING: All data (including zk_proof) must be set BEFORE calling this.
        """
        self.vk = sk.verifying_key.to_pem().hex()
        self.author = hashlib.sha256(self.vk.encode()).hexdigest()
        
        # On récupère la string JSON exacte
        data_string = self.get_data_to_sign()
        
        # On signe
        self.signature = sk.sign(data_string.encode()).hex()

    def verify(self):
        """
        Verify the confidential transaction:
        1. Verify the ECDSA signature (Identity)
        2. Verify the zk-SNARK proof (Validity of funds)
        """
        # 1. Verification de base
        if self.vk is None or self.signature is None:
            return False
        
        # 2. Vérification ECDSA (Signature)
        try:
            vk_obj = VerifyingKey.from_pem(bytes.fromhex(self.vk))
            # On vérifie exactement les mêmes données que lors de la signature
            data_string = self.get_data_to_sign()
            
            vk_obj.verify(bytes.fromhex(self.signature), data_string.encode())
            
            # Vérification que l'auteur correspond bien à la clé
            derived_author = hashlib.sha256(self.vk.encode()).hexdigest()
            if self.author != derived_author:
                return False
                
        except BadSignatureError:
            print("ERREUR: Signature ECDSA invalide.")
            return False
        
        # 3. Vérification ZK-SNARK
        # On vérifie que le prouveur possède le secret du SOLDE ACTUEL (h_old)
        # C'est la condition pour avoir le droit de dépenser.
        if self.zk_proof is None or "h_old" not in self.public_inputs:
            print("ERREUR: Preuve ZK manquante ou inputs incomplets.")
            return False
        
        # Appel au module zk_provider (py_ecc)
        # On vérifie : Est-ce que la proof correspond au commitment 'h_old' ?
        try:
            proof_valid = zk.verify_zk(self.public_inputs["h_old"], self.zk_proof)
        except Exception as e:
            print(f"ERREUR ZK Exeption: {e}")
            return False
        
        if not proof_valid:
            print("ERREUR: Preuve Zero-Knowledge mathématiquement invalide.")
            return False

        return True

    def __str__(self):
        return f"ConfidentialTx(Author={self.author[:8]}..., Proof={'OK' if self.zk_proof else 'None'})"

    def __lt__(self, other):
        return self.date < other.date

    def hash(self):
        if self.signature is None:
            raise IncompleteTransaction("No signature")
        # Le hash de la transaction inclut la signature
        full_data = self.get_data_to_sign() + self.signature
        return hashlib.sha256(full_data.encode()).hexdigest()

    @staticmethod
    def log(transactions):
        table = Table(title="Mempool / Block Transactions")
        table.add_column("Hash", style="cyan")
        table.add_column("Author", style="green")
        table.add_column("Valid?", style="magenta")

        for t in sorted(transactions):
            is_valid = t.verify() # Attention, c'est lourd à calculer pour des logs
            table.add_row(
                t.hash()[:10] + "...",
                t.author[:10] + "...",
                str(is_valid)
            )
        console = Console()
        console.print(table)


# --- TESTS CORRIGÉS ---

def test1():
    print("\n--- TEST 1 : Flux Correct (Preuve -> Signature -> Vérif) ---")
    from ecdsa import SigningKey, NIST384p
    sk = SigningKey.generate(curve=NIST384p)
    
    # 1. Données secrètes d'Alice
    secret_balance = 50
    secret_nonce = 12345
    
    # 2. Alice calcule son Commitment (h_old) qui est sur la blockchain
    # (Elle doit utiliser la lib zk pour avoir le bon format Point Elliptique)
    comm_old = zk.commit(secret_balance, secret_nonce)
    
    # 3. Alice prépare la transaction avec les Inputs Publics
    # Note : h_new et h_val seraient aussi calculés via zk.commit() dans un vrai cas
    # Ici on met des strings bidons juste pour h_new/h_val pour simplifier ce test précis
    inputs = {
        "h_old": comm_old,           # CELUI-CI EST CRUCIAL
        "h_new": "dummy_commitment", 
        "h_val": "dummy_value"
    }
    
    t = Transaction(public_inputs=inputs)
    
    # 4. Alice GÉNÈRE LA PREUVE (C'est l'étape qui manquait avant la signature)
    # Elle prouve qu'elle connait le secret de comm_old
    proof = zk.prove(secret_balance, secret_nonce)
    t.zk_proof = proof
    
    # 5. Alice SIGNE la transaction (qui contient maintenant la preuve)
    t.sign(sk)
    
    print(f"Transaction signée par {t.author[:8]}...")
    
    # 6. La Blockchain VÉRIFIE
    is_valid = t.verify()
    print(f"Résultat Vérification : {is_valid}")
    
    if is_valid:
        print(">> SUCCÈS : Transaction acceptée dans la Mempool.")
    else:
        print(">> ÉCHEC : Transaction rejetée.")

if __name__ == "__main__":
    test1()
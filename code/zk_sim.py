"""
Module ZK Provider utilisant py_ecc (Ethereum Curve).
Avantage : S'installe partout (Pure Python), pas de dépendances C.
Implémente : Pedersen Commitments & Preuves de connaissance (Schnorr).
"""
import hashlib
import json
try:
    import py_ecc.bn128 as _bn
    # core primitives
    G1 = _bn.G1
    multiply = _bn.multiply
    add = _bn.add
    curve_order = _bn.curve_order
    eq = _bn.eq
    FQ = _bn.FQ
    PYECC_AVAILABLE = True
except Exception:
    # Fallback: if py_ecc is not available, we will use SHA256-based simulation
    PYECC_AVAILABLE = False

# --- CONSTANTES MATHÉMATIQUES ---

if PYECC_AVAILABLE:
    G = G1
    # H is a second generator derived deterministically from G
    H = multiply(G, 1234567890123456789)
    ORDER = curve_order
else:
    G = None
    H = None
    ORDER = 2 ** 256

def _coerce_to_int(x):
    """Coerce various input types to an integer modulo ORDER.

    Supports int, bytes, str (tries int() then SHA256 hash), and falls back to hashing.
    """
    if isinstance(x, int):
        return x % ORDER
    if isinstance(x, bytes):
        try:
            return int.from_bytes(x, 'big') % ORDER
        except Exception:
            return int(hashlib.sha256(x).hexdigest(), 16) % ORDER
    if isinstance(x, str):
        try:
            return int(x, 0) % ORDER
        except Exception:
            return int(hashlib.sha256(x.encode()).hexdigest(), 16) % ORDER
    return int(hashlib.sha256(str(x).encode()).hexdigest(), 16) % ORDER

def _to_bytes(n):
    """Utilitaire pour convertir entier -> bytes pour le hachage"""
    return n.to_bytes(32, 'big')

def _hash_points(*args):
    """Hash cryptographique de plusieurs points ou entiers (Fiat-Shamir)"""
    hasher = hashlib.sha256()
    for arg in args:
        if hasattr(arg, '__iter__'): # C'est un point (x, y)
            # serialize point deterministically
            hasher.update(serialize_point(arg).encode())
        elif isinstance(arg, int):
            hasher.update(_to_bytes(arg))
        else:
            hasher.update(str(arg).encode())
    return int(hasher.hexdigest(), 16) % ORDER


def serialize_point(point):
    """Serialize an EC point to a hex string 'x:y' in affine coords."""
    if not PYECC_AVAILABLE:
        raise RuntimeError("py_ecc not available")
    ax, ay = normalize_point(point)
    x = int(ax)
    y = int(ay)
    return f"{x:x}:{y:x}"


def deserialize_point(s):
    """Deserialize a point serialized with serialize_point."""
    if not PYECC_AVAILABLE:
        raise RuntimeError("py_ecc not available")
    x_hex, y_hex = s.split(":")
    x = FQ(int(x_hex, 16))
    y = FQ(int(y_hex, 16))
    # Return affine point (x, y) as expected by py_ecc arithmetic
    return (x, y)


def normalize_point(point):
    """Normalize a curve point to affine (x, y).

    Works whether the point is already affine (x, y) or Jacobian (x, y, z).
    """
    if not PYECC_AVAILABLE:
        raise RuntimeError("py_ecc not available")
    # affine point
    if len(point) == 2:
        return point[0], point[1]
    # Jacobian/projective point (x, y, z)
    x, y, z = point
    try:
        # FQ objects support inversion
        z_inv = z.inv()
        return x * z_inv, y * z_inv
    except Exception:
        # z may be integer 1
        if z == 1:
            return x, y
        # fallback: return as-is (best-effort)
        return x, y

# --- FONCTIONS PUBLIQUES (API) ---

def commit(value, blinding_factor):
    """
    Crée un Pedersen Commitment (Le coffre-fort public).
    C = value*G + blinding*H
    """
    # Coerce value/blinding to integers when necessary (support string nonces)
    v = _coerce_to_int(value)
    r = _coerce_to_int(blinding_factor)
    
    # Mathématiques de courbe elliptique : v*G + r*H
    term1 = multiply(G, v)
    term2 = multiply(H, r)
    commitment = add(term1, term2)
    # return serialized form
    return serialize_point(commitment)


def commit_point(value, blinding_factor):
    """Return raw EC point (internal use)."""
    v = _coerce_to_int(value)
    r = _coerce_to_int(blinding_factor)
    term1 = multiply(G, v)
    term2 = multiply(H, r)
    return add(term1, term2)

def add_commitments(comm1_hex, comm2_hex):
    """
    Additionne deux commitments (Points Elliptiques) sous format Hex.
    Propriété Homomorphe : C(a) + C(b) = C(a + b)
    """
    if not PYECC_AVAILABLE:
        # Simulation simpliste si pas de py_ecc (Juste pour éviter le crash)
        return hashlib.sha256((comm1_hex + comm2_hex).encode()).hexdigest()

    # 1. Désérialiser les strings hex en Objets Points
    p1 = deserialize_point(comm1_hex)
    p2 = deserialize_point(comm2_hex)
    
    # 2. Additionner les points (Maths Elliptiques)
    sum_point = add(p1, p2)
    
    # 3. Renvoyer en string hex
    return serialize_point(sum_point)

def prove_knowledge(commitment, value, blinding_factor):
    """
    Génère une preuve ZK (Schnorr Proof).
    Prouve qu'on connait v et r tels que C = vG + rH, sans révéler v ni r.
    """
    # 1. Préparation (Nombres aléatoires temporaires)
    # Dans un vrai système, utilisez os.urandom. Ici fixe pour débug ou random simple.
    import random
    t_v = random.randint(1, ORDER - 1)
    t_r = random.randint(1, ORDER - 1)
    
    # 2. Calcul de l'engagement temporaire T = t_v*G + t_r*H
    T = add(multiply(G, t_v), multiply(H, t_r))
    
    # 3. Calcul du "Challenge" (c) via Fiat-Shamir Heuristic
    # Le challenge dépend du commitment public et de l'engagement temporaire
    # Accept commitment as serialized or as a point
    if isinstance(commitment, str):
        commitment_point = deserialize_point(commitment)
    else:
        commitment_point = commitment
    challenge = _hash_points(G, H, commitment_point, T)
    
    # 4. Calcul des réponses (s_v, s_r) pour masquer les secrets
    # s = t + c * secret (modulo ORDER)
    v_int = _coerce_to_int(value)
    r_int = _coerce_to_int(blinding_factor)
    s_v = (t_v + challenge * v_int) % ORDER
    s_r = (t_r + challenge * r_int) % ORDER

    # La preuve est l'ensemble (T, s_v, s_r) — on renvoie des valeurs sérialisées
    return {
        "T": serialize_point(T),
        "s_v": format(s_v, 'x'),
        "s_r": format(s_r, 'x'),
        "C": serialize_point(commitment_point)
    }

def verify(commitment, proof):
    """
    Vérifie la preuve ZK.
    """
    try:
        # Deserialize proof fields (they are serialized for JSON friendliness)
        T_ser = proof.get("T")
        s_v_ser = proof.get("s_v")
        s_r_ser = proof.get("s_r")

        T = deserialize_point(T_ser) if isinstance(T_ser, str) else T_ser
        s_v = int(s_v_ser, 16) if isinstance(s_v_ser, str) else int(s_v_ser)
        s_r = int(s_r_ser, 16) if isinstance(s_r_ser, str) else int(s_r_ser)

        commitment_point = deserialize_point(commitment) if isinstance(commitment, str) else commitment

        # 1. Recalculate the challenge
        challenge = _hash_points(G, H, commitment_point, T)

        # 2. Check: s_v*G + s_r*H == T + c*Commitment
        left = add(multiply(G, s_v), multiply(H, s_r))
        right = add(T, multiply(commitment_point, challenge))
        return eq(left, right)
    except Exception as e:
        print(f"Erreur de vérification: {e}")
        return False


def prove(value, blinding_factor):
    """High-level prove() used by the rest of the code.
    Returns a dict containing the serialized commitment and proof."""
    if not PYECC_AVAILABLE:
        # fallback: return simple SHA-based proof (legacy)
        combined = f"{value}:{blinding_factor}"
        commitment = hashlib.sha256(combined.encode()).hexdigest()
        return {"C": commitment, "secret": value, "nonce": blinding_factor}
    # create commitment and proof
    C = commit(value, blinding_factor)
    proof = prove_knowledge(C, value, blinding_factor)
    return proof


def verify_zk(public_commitment, proof):
    """High-level verification wrapper used by transaction.verify()."""
    if not PYECC_AVAILABLE:
        # legacy check: SHA256(secret:nonce) == public_commitment
        try:
            return hashlib.sha256(f"{proof['secret']}:{proof['nonce']}".encode()).hexdigest() == public_commitment
        except Exception:
            return False
    return verify(public_commitment, proof)
import zk_sim

print('py_ecc available:', getattr(zk_sim, 'PYECC_AVAILABLE', False))

# choose a value and blinding
value = 40
blinding = 13

proof = zk_sim.prove(value, blinding)
commitment = proof.get('C') if isinstance(proof, dict) else None
print('Proof produced:', proof)
print('Public commitment:', commitment)

ok = zk_sim.verify_zk(commitment, proof)
print('verify_zk ->', ok)

# Negative test: tamper proof
if isinstance(proof, dict):
    bad = proof.copy()
    # if EC mode, change s_v; if SHA fallback, change secret
    if zk_sim.PYECC_AVAILABLE:
        bad['s_v'] = format((int(bad['s_v'], 16) + 1) % zk_sim.ORDER, 'x')
    else:
        bad['secret'] = '9999'
    print('verify tampered ->', zk_sim.verify_zk(commitment, bad))

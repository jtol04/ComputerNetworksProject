import hashlib, json

DIFFICULTY = "0000"

def sha256(data):
    return hashlib.sha256(data).hexdigest()

def hash_json(obj):
    return sha256(json.dumps(obj, sort_keys=True).encode())

def pow_ok(h):
    return h.startswith(DIFFICULTY)
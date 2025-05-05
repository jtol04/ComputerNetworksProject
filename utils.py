"""
utils.py

Utility functions for hashing and proof-of-work checks in the RPS blockchain project.
"""

import hashlib
import json

# Proof-of-work difficulty target
DIFFICULTY = "0000"

def sha256(data):
    """
    Compute SHA-256 hash of given bytes.

    Args:
        data (bytes): Input data to hash.

    Returns:
        str: Hexadecimal SHA-256 digest.
    """
    return hashlib.sha256(data).hexdigest()

def hash_json(obj):
    """
    Produce a deterministic hash for a JSON-serializable object.

    Args:
        obj (object): Python object serializable to JSON.

    Returns:
        str: Hexadecimal SHA-256 digest of sorted JSON representation.
    """
    return sha256(json.dumps(obj, sort_keys=True).encode())

def pow_ok(h):
    """
    Check if a given block header hash meets the proof-of-work difficulty.

    Args:
        header_hash (str): Hexadecimal hash string to check.

    Returns:
        bool: True if hash starts with the difficulty target, False otherwise.
    """
    return h.startswith(DIFFICULTY)
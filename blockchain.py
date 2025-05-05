"""
blockchain.py

Core blockchain logic for the Rock-Paper-Scissors application.
Defines Block and Blockchain classes with PoW mining, validation, and chain reorganization.
"""

import json
import time

from utils import sha256, hash_json, pow_ok

class Block:
    """
    Represents a single block in the blockchain.
    """
    def __init__(self, index, prev, transactions, 
                 nonce=0, timestamp=None):
        """
        Initialize a new Block.

        Args:
            index (int): Height of the block in the chain.
            prev (str): Hash of the previous block's header.
            transactions (list): List of transaction dictionaries.
            nonce (int, optional): Proof-of-work nonce. Defaults to 0.
            timestamp (int, optional): Unix timestamp. Defaults to current time.
        """
        self.index = index
        self.prev = prev
        self.transactions = transactions
        self.nonce = nonce
        self.timestamp = timestamp if timestamp is not None else int(time.time())

    def header(self):
        """
        Return the block header as a dictionary.
        """
        return {
            "index": self.index,
            "prev": self.prev,
            "transactions": self.transactions,
            "timestamp": self.timestamp,
            "nonce": self.nonce
        }
    
    def header_hash(self):
        """
        Compute the SHA-256 hash of the block header.
        """
        return sha256(json.dumps(self.header(), sort_keys=True).encode())
    
    def mine(self):
        """
        Increment nonce until proof-of-work condition is met.
        """
        while not pow_ok(self.header_hash()):
            self.nonce += 1
    
    def to_json(self):
        """
        Serialize the block to a JSON string.
        """
        return json.dumps({"header": self.header(),
                                           "transactions": self.transactions})

    @staticmethod
    def from_json(js):
        """
        Deserialize a JSON string into a Block instance.
        """
        d = json.loads(js); h = d["header"]
        return Block(h["index"], h["prev"], d["transactions"],
                     h["nonce"], h["timestamp"])
    
class Blockchain:
    """
    Manages the chain of blocks and handles validation and reorganization.
    """
    def __init__(self):
        """
        Create a new Blockchain with a mined genesis block.
        """
        # starting block
        genesis = Block(
          index=0,
          prev="0"*64,
          transactions=[{"type":"GENESIS"}],
          timestamp=0
        )
        # mine it so the same difficulty rule applies
        genesis.mine()
        self.chain = [genesis]

    @staticmethod
    def _winner(move_a, move_b):
        """
        Determine the winner between two moves.

        Returns:
            int: 0 for tie, 1 if move_a wins, 2 if move_b wins.
        """
        if move_a == move_b:
            return 0          # tie
        beats = {"rock":"scissors", "scissors":"paper", "paper":"rock"}
        return 1 if beats[move_a] == move_b else 2

    def _valid(self, blk, prev):
        """
        Validate a block against its previous block and game rules.

        Args:
            blk (Block): Block to validate.
            prev (Block): Previous block in the chain.

        Returns:
            bool: True if valid, False otherwise.
        """
        # 1. chain linkage & PoW
        if blk.index != prev.index + 1:        return False
        if blk.prev  != prev.header_hash():    return False
        if not pow_ok(blk.header_hash()):      return False

        # Skip validation for genesis block
        if blk.index == 0:
            return True

        # Group transactions by match_id
        match_txs = {}
        for tx in blk.transactions:
            if "match_id" in tx:
                match_id = tx["match_id"]
                if match_id not in match_txs:
                    match_txs[match_id] = []
                match_txs[match_id].append(tx)
    
        # Validate each match separately
        for match_id, txs in match_txs.items():
            commits = {}
            reveals = []
            result = None
        
            # Extract commits
            for tx in txs:
                if tx["type"] == "COMMIT":
                    commits[(tx["match_id"], tx["peer"])] = tx["hash"]
        
            # Check reveals against commits and collect result
            for tx in txs:
                if tx["type"] == "REVEAL":
                    key = (tx["match_id"], tx["peer"])
                    if key not in commits:
                        return False  # Missing commit
                
                    keyhash = sha256((tx["move"] + tx["key"]).encode())
                    if commits[key] != keyhash:
                        return False  # Bad commit
                
                    reveals.append(tx)
                elif tx["type"] == "RESULT":
                    result = tx
        
            # We need exactly 2 reveals and 1 result for a valid match
            if len(reveals) == 2 and result is not None:
                # Verify result correctness
                a, b = sorted(reveals, key=lambda t: t["peer"])  # deterministic order
            
                if a["move"] == b["move"]:
                    exp_winner, exp_tie = 0, True
                elif self._winner(a["move"], b["move"]) == 1:
                    exp_winner, exp_tie = a["peer"], False
                else:
                    exp_winner, exp_tie = b["peer"], False
            
                if result["winner"] != exp_winner or result["tie"] != exp_tie:
                    return False  # Invalid result
    
        return True

    def add(self, blk):
        """
        Attempt to add or reorganize the chain with a new block.

        Returns:
            bool: True if chain was modified, False otherwise.
        """
        tip = self.chain[-1]
        prev = blk.prev[:12]
        tip_hash = tip.header_hash()[:12]
        second_hash = (self.chain[-2].header_hash()[:12]
                       if len(self.chain) >= 2 else None)
        print(f"[DEBUG add] blk.index={blk.index}, blk.prev={prev}, tip={tip_hash}, parent={second_hash}")

        # case 1: normal append
        if blk.prev == tip.header_hash():
            print("  trying case1 append")
            if self._valid(blk, tip):
                print("  -> case1 valid, appending")
                self.chain.append(blk)
                return True
            print("  -> case1 invalid")
            return False

        # case 2: fork of depth-1
        if len(self.chain) >= 2 and blk.prev == self.chain[-2].header_hash():
            # block’s prev points to the second‐to‐last block in your chain (i.e. it “skipped” the current tip).
            print("  trying case 2: fork of depth 1 detected")
            if not self._valid(blk, self.chain[-2]):
                print("  -> case2 invalid")
                return Falsegit
            if blk.header_hash() < tip.header_hash():
                print("  -> case2 valid & better PoW, reorganize")
                self.chain[-1] = blk
                return True
            else:
                print("  -> case2 valid but worse PoW, keep old tip")
            return False
        print("  -> no matching case")

        return False

    # for debugging
    def print_chain(self):
        """
        Nicely print every block in the current main chain.
        """
        for blk in self.chain:
            print("-"*60)
            print(f"Block #{blk.index}")
            print("Header:")
            print(json.dumps(blk.header(), indent=2))
            print("Transactions:")
            print(json.dumps(blk.transactions, indent=2))
        print("-"*60)
    
    # helpers
    def height(self):
        """
        Return the current chain height (last block index).
        """
        return len(self.chain)-1
    def tip(self):
        """
        Return the hash of the current tip block.
        """  
        return self.chain[-1].header_hash()


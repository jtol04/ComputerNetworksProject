import json
import time
from utils import sha256, hash_json, pow_ok

class Block:
    def __init__(self, index, prev, transactions, 
                 nonce=0, timestamp=None):
        self.index = index
        self.prev = prev
        self.transactions = transactions
        self.nonce = nonce
        self.timestamp = timestamp if timestamp is not None else int(time.time())

    def header(self):
        return {
            "index": self.index,
            "prev": self.prev,
            # "root": 0,       # add later for merkle
            "timestamp": self.timestamp,
            "nonce": self.nonce
        }
    
    def header_hash(self):
        return sha256(json.dumps(self.header(), sort_keys=True).encode())
    
    def mine(self):
        while not pow_ok(self.header_hash()):
            self.nonce += 1
    
    def to_json(self):  return json.dumps({"header": self.header(),
                                           "transactions": self.transactions})

    @staticmethod
    def from_json(js):
        d = json.loads(js); h = d["header"]
        return Block(h["index"], h["prev"], d["transactions"],
                     h["nonce"], h["timestamp"])
    
class Blockchain:
    def __init__(self):
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
        if move_a == move_b:
            return 0          # tie
        beats = {"rock":"scissors", "scissors":"paper", "paper":"rock"}
        return 1 if beats[move_a] == move_b else 2

    def _valid(self, blk, prev):
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
            print("  trying case 2: fork of depth 1 detected")
            if not self._valid(blk, self.chain[-2]):
                print("  -> case2 invalid")
                return False
            if blk.header_hash() < tip.header_hash():
                print("  -> case2 valid & better PoW, reorganize")
                self.chain[-1] = blk
            else:
                print("  -> case2 valid but worse PoW, keep old tip")
            return True


        print("  -> no matching case")
        return False

    # for debugging
    def print_chain(self):
        """Nicely print every block in the current main chain."""
        for blk in self.chain:
            print("-"*60)
            print(f"Block #{blk.index}")
            print("Header:")
            print(json.dumps(blk.header(), indent=2))
            print("Transactions:")
            print(json.dumps(blk.transactions, indent=2))
        print("-"*60)
    
    # helpers
    def height(self): return len(self.chain)-1
    def tip(self):    return self.chain[-1].header_hash()


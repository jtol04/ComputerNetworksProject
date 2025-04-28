import time
from utils import sha256, hash_json

class Block:
    def __init__(self, index, prev, transactions, 
                 nonce=0, timestamp=None):
        self.index = index
        self.prev = prev
        self.transactions = transactions
        self.nonce = nonce
        self.timestamp = timestamp or int(time.time())

    def header(self):
        return {
            "index": self.index,
            "prev": self.prev,
            "root": 0,       # add later
            "timestamp": self.timestamp,
            "nonce": self.nonce
        }
    
    def header_hash(self):
        return sha256(json.dumps(self.header(), sort_keys=True).encode())
    
class Blockchain:
    def __init__(self):
        genesis = Block(0, "0"*64, [{"type":"GENESIS"}])
        genesis.mine()
        self.chain = [genesis]
    
    # helpers
    def height(self): return len(self.chain)-1
    def tip(self):    return self.chain[-1].header_hash()
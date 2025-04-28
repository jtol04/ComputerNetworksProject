import time

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
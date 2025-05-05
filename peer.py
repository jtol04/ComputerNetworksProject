"""
peer.py

Peer node logic for the Rock-Paper-Scissors blockchain application.
Handles network connections, commit-reveal protocol, block proposals,
and chain synchronization with proof-of-work and fork resolution.
"""

import secrets
import socket
import json
import threading
import random
import time

from blockchain import Blockchain, Block

from utils import sha256, hash_json, pow_ok
from threading import Condition
from global_vars import TRACKER_PORT


class Peer:
    """
    Represents a peer in the RPS blockchain network.

    Manages matchmaking, commit-reveal game protocol,
    block mining, and network synchronization.
    """
    # Constants
    CHOICES = ['rock', 'paper', 'scissors']
    OUTCOMES = {
        'rockrock': 'tie',
        'rockpaper': 'lost',
        'rockscissors': 'win',
        'paperrock': 'win',
        'paperpaper': 'tie',
        'paperscissors': 'lost',
        'scissorsscissors': 'tie',
        'scissorsrock': 'lost',
        'scissorspaper': 'win'
    }

    def __init__(self, host='localhost', tracker_port=TRACKER_PORT):
        """
        Initialize the Peer with network settings and blockchain state.

        Args:
            host (str): Address of the tracker server.
            tracker_port (int): Port of the tracker server.
        """
        # Network connection properties
        self.host = host
        self.tracker_port = tracker_port
        self.tracker_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listen_socket.bind((host, 0))
        self.game_port = self.listen_socket.getsockname()[1]
        self.listen_socket.listen()

        print(f"Listen Socket bound to port {self.game_port}")

        # Connection state
        self.connected = False
        self.peer_id = None
        self.network_peers = {}

        # Game state
        self.opponent_id = None
        self.match_result = None
        self.current_match_id = None
        self.commits = {}

        # Blocks
        self.blockchain = Blockchain()
        self.buffer = []
        self.pending = []
        self.lock = threading.Lock()
        self.should_broadcast = True
        self.cond = Condition()

    def _send_once(self, addr, port, obj):
        """
        Send a single JSON message over TCP and close the connection.

        Args:
            addr (str): Destination address.
            port (int): Destination port.
            message (dict): JSON message.
        """
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((addr, port))
            s.send(json.dumps(obj).encode() + b'\n')
        finally:
            s.close()

    def _clean_buffer(self, block):
        """
        Remove transactions from the buffer that are included in the given block.

        Args:
            block (Block): Block whose transactions to remove.
        """
        txids_in_block = {(tx.get("match_id", ""), tx.get("type", ""), tx.get("peer", 0))
                          for tx in block.transactions if "type" in tx}

        # Keep only transactions not in the block
        self.buffer = [tx for tx in self.buffer if
                       (tx.get("match_id", ""), tx.get("type", ""), tx.get("peer", 0))
                       not in txids_in_block]

    def handle_peer_connections(self):
        """
        Accept incoming peer connections and spawn handler threads.
        """

        print(f"Listening for peer messages on port {self.game_port}")
        while self.connected:
            print(f"WAITING FOR PEER CONNECTIONS ON PORT {self.game_port}")
            client_socket, address = self.listen_socket.accept()
            print(f"Accepted connection from {address}")
            thread = threading.Thread(target=self.handle_peer_message, args=(client_socket,))
            thread.daemon = True
            thread.start()

    def handle_peer_message(self, client_socket):
        """
        Process messages from another peer over a socket.

        Args:
            client_socket (socket.socket): Connected socket.
        """
        buffer = ""
        while True:
            print("Reading message from peer...")
            chunk = client_socket.recv(4096).decode()
            if not chunk:
                break
            buffer += chunk

            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if not line.strip():
                    continue
                msg = json.loads(line)

                # ----- store game transactions -----
                if msg["type"] in ("COMMIT", "REVEAL", "RESULT"):
                    self.buffer.append(msg)
                    if msg["type"] == "COMMIT":
                        self.commits[(msg["match_id"], msg["peer"])] = msg["hash"]
                    print(f"Received peer message: {msg}")

                elif msg["type"] == "BLOCK_PROPOSAL":
                    sender = msg["peer"]
                    blk = Block.from_json(msg["block"])

                    # check if block proposal is from match oppoent
                    is_opponent = self.current_match_id is not None and \
                                  any(t["type"] == "RESULT" and t["match_id"] == self.current_match_id
                                      for t in blk.transactions)

                    print(f"[DEBUG peer] got BLOCK_PROPOSAL for block {blk.index} from {sender}")

                    # grab the lock
                    with self.cond:
                        self.should_broadcast = False

                        # add block proposal to local block chain
                        self.blockchain.add(blk)
                        self._clean_buffer(blk)
                        #self.blockchain.print_chain()

                        if is_opponent:
                            self.end_game()
                            self.current_match_id = None

                        # ensure there arent any pending blocks
                        got_pending = self.cond.wait_for(lambda: bool(self.pending), timeout=0.3)

                        if not got_pending:
                            print(f"[{self.peer_id}] no pending blocks to remine")
                        else:
                            # remine pending block
                            pending_blk = self.pending.pop(0)
                            old_index = pending_blk.index
                            pending_blk.index = self.blockchain.height() + 1
                            pending_blk.prev = self.blockchain.tip()
                            pending_blk.nonce = 0
                            pending_blk.mine()

                            print(f"[{self.peer_id}] remined pending blk #{old_index} to new blk #{pending_blk.index}")
                            self.blockchain.add(pending_blk)
                            #self.blockchain.print_chain()
                            self._clean_buffer(pending_blk)

                            # broadcast the remined block
                            print(f"[{self.peer_id}] broadcasting to peers blk #{pending_blk.index}")
                            for pid, info in self.network_peers.items():
                                if pid == self.peer_id: continue
                                self._send_once(
                                    info["address"], info["port"],
                                    {"type": "BLOCK_PROPOSAL", "peer": self.peer_id, "block": pending_blk.to_json()}
                                )


                elif msg["type"] == "CHAIN_REQUEST":
                    chain_json = [blk.to_json() for blk in self.blockchain.chain]
                    response = {
                        "type": "CHAIN_RESPONSE",
                        "chain": chain_json,
                        "from_peer": self.peer_id
                    }
                    addr = msg["reply_addr"]
                    port = msg["reply_port"]
                    self._send_once(addr, port, response)

                elif msg["type"] == "CHAIN_RESPONSE":
                    # peer sent their chain
                    new_chain = []
                    sender = msg["from_peer"]
                    for blk_json in msg["chain"]:
                        new_chain.append(Block.from_json(blk_json))

                    print(f"[{self.peer_id}] adopting chain of length {len(new_chain)} from {sender}")
                    self.blockchain.chain = new_chain

                    # need to double check cleaning the buffer
                    for blk in new_chain:
                        self._clean_buffer(blk)

    def self_check(self):
        """
        Detect errors in the node’s local blockchain (e.g. a shorter blockchain, duplicate blocks, 
        etxra blocks)
        """
        for i in range(1, len(self.blockchain.chain)):
            # check index
            if self.blockchain.chain[i].index != i:
                return False
            # check hash
            if self.blockchain.chain[i].prev != self.blockchain.chain[i - 1].header_hash():
                return False
            # check proof of work
            if not pow_ok(self.blockchain.chain[i].header_hash()):
                return False

        hashes = [blk.header_hash() for blk in self.blockchain.chain]
        if len(hashes) != len(set(hashes)):
            return False

        return True

    def request_full_chain(self, target_peer_id):
        """
        Ask peer with longest chain to send their blockchain
        """
        info = self.network_peers[target_peer_id]
        request = {
            "type": "CHAIN_REQUEST",
            "from_peer": self.peer_id,
            "reply_addr": self.host,
            "reply_port": self.game_port
        }
        self._send_once(info["address"], info["port"], request)

    def play_match(self, opp_addr, opp_port, match_id):
        """
        Connects to the opponent, sends opponent the choice,
        Receives opponents choice, and finally logs the win or loss
        """

        #self.blockchain.print_chain()
        self.should_broadcast = True

        self.opponent_id = next(
            pid for pid in self.network_peers.keys()
            if pid != self.peer_id and
            self.network_peers[pid]["address"] == opp_addr and
            self.network_peers[pid]["port"] == opp_port
        )
        self.current_match_id = match_id
        move = random.choice(self.CHOICES)
        key = secrets.token_hex(4)  # 8-char random key

        # COMMIT - hide move
        commit = {
            "type": "COMMIT",
            "match_id": match_id,
            "peer": self.peer_id,
            "hash": sha256((move + key).encode()),
        }

        self.buffer.append(commit)
        self.commits[(match_id, self.peer_id)] = commit["hash"]
        self._send_once(opp_addr, opp_port, commit)

        # wait for opponent commit
        while not any(
                t["type"] == "COMMIT" and t["match_id"] == match_id and t["peer"] != self.peer_id
                for t in self.buffer
        ):
            time.sleep(0.05)

        # REVEAL - show move + key
        reveal = {
            "type": "REVEAL",
            "match_id": match_id,
            "peer": self.peer_id,
            "move": move,
            "key": key,
        }

        self.buffer.append(reveal)
        self._send_once(opp_addr, opp_port, reveal)

        # wait for opponent reveal
        while not any(
                t["type"] == "REVEAL" and t["match_id"] == match_id and t["peer"] != self.peer_id
                for t in self.buffer
        ):
            time.sleep(0.05)
        opp = next(
            t
            for t in self.buffer
            if t["type"] == "REVEAL" and t["match_id"] == match_id and t["peer"] != self.peer_id
        )

        # RESULT – decide winner
        outcome = self.OUTCOMES[move + opp["move"]]
        result = {
            "type": "RESULT",
            "match_id": match_id,
            "winner": self.peer_id
            if outcome == "win"
            else opp["peer"]
            if outcome == "lost"
            else 0,
            "tie": outcome == "tie",
        }
        self.buffer.append(result)

        print(f"[{self.peer_id}] moves: {move} vs {opp['move']} → {outcome}")

        # MINING - lower peer ID mines the block
        if (self.peer_id < self.opponent_id):
            stored_height = self.blockchain.height() + 1
            blk = Block(
                self.blockchain.height() + 1,
                self.blockchain.tip(),
                transactions=self.buffer.copy()
            )
            blk.mine()  # busy‐loop incrementing nonce until pow_ok()
            print(f"[{self.peer_id}] mined block #{blk.index} {blk.header_hash()[:12]}…")

            # grab the lock
            with self.cond:
                if self.should_broadcast:
                    # check if should_broadcast has been set to false, for a max of 0.2s
                    # no propposals received yet. broadcast to all peers
                    print(f"No proposals received. Broadcasting to peers.")
                    for pid, info in self.network_peers.items():
                        if pid == self.peer_id:  # skip myself
                            continue
                        self._send_once(info["address"], info["port"],
                                        {"type": "BLOCK_PROPOSAL", "peer": self.peer_id, "block": blk.to_json()})

                    print(f"[{self.peer_id}] broadcased first. adding block #{blk.index} to local chain")
                    self.blockchain.add(blk)
                else:
                    # someone else broadcasted first. need to remine.
                    print(f"[{self.peer_id}] added block #{blk.index} to pending block list")
                    self.pending.append(blk)
                    # let the handler know it can wake up immediately
                    self.cond.notify_all()

        local_blockchain = {
            "type": "blockchain_update",
            "peer_id": self.peer_id,
            "local_blockchain": [block.to_json() for block in self.blockchain.chain]
        }

        self.tracker_socket.send((json.dumps(local_blockchain) + "\n").encode())
        self.end_game()
        self.buffer.clear()

    def listen_for_tracker(self):
        """
        Thread to listen for messages from the tracker
        """
        buffer = ""
        while self.connected:
            chunk = self.tracker_socket.recv(4096).decode()
            if not chunk:  # i.e tracker closed
                break
            buffer += chunk
            # process one line at a time
            while "\n" in buffer:
                line, buffer = buffer.split("\n", 1)
                if line.strip():
                    self.handle_tracker_message(json.loads(line))

    def connect_to_tracker(self):
        """
        Connect to the tracker and send an init message
        """
        self.tracker_socket.connect((self.host, self.tracker_port))

        init_message = {
            'type': 'init',
            'game_port': self.game_port
        }
        self.tracker_socket.send((json.dumps(init_message) + "\n").encode())

        self.connected = True
        print(f"Connected to tracker at address: {self.host}:{self.tracker_port}")

        self.tracker_thread = threading.Thread(target=self.listen_for_tracker)
        self.tracker_thread.daemon = True
        self.tracker_thread.start()

        # Start peer message listener 
        self.peer_thread = threading.Thread(target=self.handle_peer_connections)
        self.peer_thread.daemon = True
        self.peer_thread.start()

    def handle_tracker_message(self, message):
        """
        Thread to handle messages from the tracker
        """
        if message['type'] == 'peer_id':
            self.peer_id = message['peer_id']
            print(f"Assigned peer ID: {self.peer_id}")

        elif message['type'] == 'network_update':
            self.network_peers = {}
            for peer_id, info in message['peers'].items():
                self.network_peers[int(peer_id)] = {
                    'address': info['address'],
                    'port': info['port']
                }

        elif message['type'] == 'match_start':
            print("MATCH STARTING")
            print(f"Match ID: {message['match_id']}")
            print(f"Opponent ID: {message['opponent_id']}")
            print(f"Opponent address: {message['opponent_addr']}:{message['opponent_game_port']}")

            self.opponent_id = message['opponent_id']
            # Start play match thread between peers
            opp_addr, opp_port = message["opponent_addr"], message["opponent_game_port"]
            threading.Thread(
                target=self.play_match, args=(opp_addr, opp_port, message["match_id"]), daemon=True
            ).start()

    def end_game(self):
        """
        End the game and send the result to the tracker
        """
        print("ENDING GAME")
        # Find the match result from the blockchain
        last_block = self.blockchain.chain[-1]
        match_result = next(
            (t for t in last_block.transactions if t["type"] == "RESULT" and t["match_id"] == self.current_match_id),
            None
        )

        result_text = "tie"
        if match_result:
            if match_result["winner"] == self.peer_id:
                result_text = "win"
            elif match_result["winner"] != 0:
                result_text = "loss"

        game_result = {
            'type': 'game_end',
            'peer_id': self.peer_id,
            'opponent_id': self.opponent_id,
            'match_id': self.current_match_id,
            'match_log': f'peer {self.peer_id} played peer {self.opponent_id} at {time.time()} with result {result_text}'
        }
        self.tracker_socket.send((json.dumps(game_result) + "\n").encode())
        print("Game ended - sent result to tracker")


if __name__ == "__main__":
    peer = Peer()
    peer.connect_to_tracker()
    while peer.connected:
        pass

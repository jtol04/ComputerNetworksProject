import secrets
import socket
import json
import threading
import random
import time
from blockchain import Blockchain, Block
from utils import sha256, hash_json

class Peer:
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

    def __init__(self, host='localhost', tracker_port=10000):
        """
        Initialize peer with connection details
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

        # Blocks
        self.blockchain = Blockchain()
        self.buffer = []

    def handle_peer_connections(self):
        """
        Thread to handle incoming peer connections (one thread spins up for each peer)
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
        Handle a message from another peer
        """
        while True:
            print("Reading message from peer...")
            data = client_socket.recv(1024).decode()
            if not data:
                break
            print(f"Received peer message: {data}")


    def play_match(self, opp_addr, opp_port, match_id):
        """
        Connects to the opponent, sends opponent the choice,
        Receives opponents choice, and finally logs the win or loss
        """

        move = random.choice(self.CHOICES)
        key = secrets.token_hex(4)          # 8-char random key

        # COMMIT - hide move
        commit = {
            "type": "COMMIT",
            "match_id": match_id,
            "peer": self.peer_id,
            "hash": sha256((move + key).encode()),
        }

        self.buffer.append(commit)
        self._send_once(opp_addr, opp_port, commit)

        # wait for opponent commit
        while not any(
            t["type"] == "COMMIT" and t["match_id"] == match_id and t["peer"] != self.peer_id
            for t in self.buffer
        ):
            time.sleep(0.05)
            
        self.buffer.clear()


    def listen_for_tracker(self):
        """
        Thread to listen for messages from the tracker
        """
        while self.connected:
            data = self.tracker_socket.recv(1024).decode()
            if not data:
                break
            message = json.loads(data)
            self.handle_tracker_message(message)


    def connect_to_tracker(self):
        """
        Connect to the tracker and send an init message
        """
        self.tracker_socket.connect((self.host, self.tracker_port))
        
        init_message = {
            'type': 'init',
            'game_port': self.game_port
        }
        self.tracker_socket.send(json.dumps(init_message).encode())
        
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

            # Start play match thread between peers
            opp_addr, opp_port = message["opponent_addr"], message["opponent_game_port"]
            threading.Thread(
                target=self.play_match, args=(opp_addr, opp_port,  message["match_id"]), daemon=True
            ).start()
            
    def end_game(self):
        """
        End the game and send the result to the tracker
        """
        print("ENDING GAME")

        game_result = {
            'type': 'game_end',
            'peer_id': self.peer_id,
            'match_log': f'peer {self.peer_id} played peer {self.opponent_id} at {time.time()} with result ?'
        }
        self.tracker_socket.send(json.dumps(game_result).encode())
        print("Game ended - sent result to tracker")
    

if __name__ == "__main__":
    peer = Peer()
    peer.connect_to_tracker()
    while peer.connected:
        pass

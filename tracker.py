import socket
import threading
import json
import time

class Tracker:
    def __init__(self, host='localhost', port=5000):
        self.host = host
        self.port = port
        self.peers = {}
        self.next_peer_id = 1
        self.next_match_id = 1 # increment with each match
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.available_peers = []  # Peers not currently playing       
        
        # Start matchmaking loop to match peers and run games
        self.matchmaking_thread = threading.Thread(target=self.matchmaking_loop)
        self.matchmaking_thread.daemon = True
        self.matchmaking_thread.start()
        
    def matchmaking_loop(self):
        """
        Matchmaking loop to match peers and run games
        """

        while True:
            print(f"MATCHMAKING CHECK - Available peers: {self.available_peers}")
            if len(self.available_peers) >= 2:
                print(f"Found enough peers! Starting to match from: {self.available_peers}")
                
                while len(self.available_peers) >= 2:
                    peer1_id = self.available_peers.pop(0)
                    peer2_id = self.available_peers.pop(0)
                    
                    match_id = f"match_{self.next_match_id}"                    
                    print(f"Creating match between peers {peer1_id} and {peer2_id} with id {self.next_match_id}")
                    self.next_match_id += 1
                    print(f"Starting match {match_id}")
                    self.start_match(peer1_id, peer2_id, match_id)
                    
            time.sleep(1)
            
    def start_match(self, peer1_id, peer2_id, match_id):
        """
        Start a match between two peers
        """
        peer1_data = self.peers[peer1_id]
        peer2_data = self.peers[peer2_id]
        
        self.send_to_peer(peer1_id, {
            'type': 'match_start',
            'match_id': match_id,
            'opponent_id': peer2_id,
            'opponent_addr': peer2_data['address'][0],
            'opponent_game_port': peer2_data['game_port'] 
        })
        
        self.send_to_peer(peer2_id, {
            'type': 'match_start',
            'match_id': match_id,
            'opponent_id': peer1_id,
            'opponent_addr': peer1_data['address'][0],
            'opponent_game_port': peer1_data['game_port'] 
        })
            
    def send_to_peer(self, peer_id, message):
        """
        Send a message to a specific peer
        """
        self.peers[peer_id]['socket'].send(json.dumps(message).encode())
        print(f"Message sent to peer {peer_id}") 

    def broadcast_network_update(self):
        """
        Broadcast a network update to all peers (i.e. new peer connections added/removed)
        """
        if not self.peers: 
            return
        
        network_state = {}
        for peer_id, peer_data in self.peers.items():
            network_state[peer_id] = {
                'address': peer_data['address'][0],
                'port': peer_data['game_port'],
            }
        
        message = {
            'type': 'network_update',
            'peers': network_state
        }
        
        for peer_id in self.peers:
            self.send_to_peer(peer_id, message)
            
    def handle_new_peer(self, client_socket, address):
        """
        Handle a new peer connection
        """

        peer_id = self.next_peer_id
        self.next_peer_id += 1
        
        data = client_socket.recv(1024).decode()
        init_message = json.loads(data)
        game_port = init_message['game_port']

        # add new peer to peers dict
        self.peers[peer_id] = {
            'address': address,
            'socket': client_socket,
            'game_port': game_port
        }
        
        response = {
            'type': 'peer_id',
            'peer_id': peer_id
        }
        
        client_socket.send(json.dumps(response).encode())
        
        self.available_peers.append(peer_id)
        print(f"Added peer {peer_id} to available_peers list. Current available: {self.available_peers}")
        
        self.broadcast_network_update()
        
        try:
            while True:
                data = client_socket.recv(1024).decode()
                if not data:
                    break
                    
                message = json.loads(data)
                self.handle_peer_message(peer_id, message)
                
        except Exception as e:
            print(f"Error handling peer {peer_id}: {e}")
        finally:
            if peer_id in self.peers:
                del self.peers[peer_id]
            if peer_id in self.available_peers:
                self.available_peers.remove(peer_id)
            client_socket.close()
            print(f"Peer {peer_id} disconnected")
            self.broadcast_network_update()
            
    def handle_peer_message(self, peer_id, message):
        """
        Handle messages from peers
        """
        if message['type'] == 'game_end':
            peer_id = message['peer_id']
            if peer_id not in self.available_peers:
                self.available_peers.append(peer_id)
                print(f"Peer {peer_id} is now available for new matches")
                print(f"Current available peers: {self.available_peers}")

    def start(self):
        """
        Start the tracker server
        """

        self.socket.bind((self.host, self.port))
        self.socket.listen()
        print(f"Tracker is listening on {self.host}:{self.port}")
        
        while True:
            client_socket, address = self.socket.accept()
            print(f"New connection from {address}")

            # Create a new thread for each peer
            client_thread = threading.Thread(
                target=self.handle_new_peer,
                args=(client_socket, address)
            )
            client_thread.start()

if __name__ == "__main__":
    tracker = Tracker()
    tracker.start()

# Rock Paper Scissors Blockchain

## Overview
This is a peer-to-peer implementation of Rock Paper Scissors where players connect through a central tracker and play games with each other.

## Components

### 1. Tracker Server
The tracker serves as the central matchmaking coordinater of the p2p blockchain network:
- Accept and manage peer connections
- Assign unique peer IDs to connected players
- Maintain list of available peers for matchmaking
- Match available peers into games
- Broadcast network updates when peers join/leave
- Handle game completion to update the list of available players

### 2. Peer Client
Each peer acts as both client and server, connecting to the tracker for matchmaking but communicating directly with other peers to update the blockchain
- Connect to tracker for matchmaking
- Listen for incoming connections from other peers
- Establish direct connections with other peers to maintain the blockchain
- Handle game logic and state
- Send game_end message once done


## Architecture

### Threading 
- Tracker runs 2 threads
  1. Main thread: Accepts new peer connections
  2. Matchmaking thread: Continuously matches available peers based on who is not playing

- Each peer runs multiple threads:
  - Tracker listener thread: Handles messages from tracker
  - peer listener threads: keep track of messages from each peer

### Connection 
1. Peer starts up and connects to tracker
2. Tracker assigns peer ID and adds peer to available list
3. When matched:
   - Tracker sends match info to both peers
   - Peers establish direct connection
   - Peers play game
   - Peers become available for new matches


### Blockchain
- Each peer will mine its own blocks 
- Each peer will first commit its move to prevent cheating
- once a peer and its oponnent are commited, it can add the reveal blocks to the block chain (each peer on its own)
- given each peer is adding its own we will need some nice logic (i.e. forking) to handle discrepencies. 

### Forking
- TODO: how do we want to do forking


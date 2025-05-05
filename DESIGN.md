# Rock Paper Scissors Blockchain

## Overview
This is a peer-to-peer implementation of Rock Paper Scissors where players connect through a central tracker and play games with each other.

## Components

### 1. Tracker Server
The tracker serves as the central matchmaking coordinater of the P2P blockchain network:
- Accept and manage peer connections
- Assign unique peer IDs to connected players
- Maintain list of available peers for matchmaking
- Randomly match available peers into games
- Broadcast network updates when peers join/leave
- Handle game completion to update the list of available players

### 2. Peer Client
Each peer acts as both client and server, connecting to the tracker for matchmaking but communicating directly with other peers to update the blockchain
- Connect to tracker for matchmaking
- Listen for incoming connections from other peers
- Establish direct connections with other peers to maintain the blockchain
- Handle game logic and state
- Send game_end message once done
- Assigned miners per match broadcast mined blocks to all peers to their network

### 3. Demo Application Design
The Graphical User Interface brings our blockchain protocol to life. Along with periodic updates of each peer's
local blockchain, we've implemented a leaderboard that keeps track of how many wins each peer has. Furthermore,
clicking on each block details the transactions (e.g. commit and reveal) that occured for that match. Green blocks indicate a player has won whereas blue blocks indicate a tie. The User Interface demonstrates how all peers have the same local blockchain. Though some may be ahead of the blockchain "race", everyone eventually catches up and stores the same matches at the right order.*

* assuming the right conditions (e.g. all peers initialized right at the same time)

## Architecture

### Threading 
- Tracker runs 2 threads
  1. Main thread: Accepts new peer connections
  2. Matchmaking thread: Continuously matches available peers based on who is not playing

- Each peer runs multiple threads:
  1. Tracker listener thread: Handles messages from tracker
  2. Peer listener threads: keep track of messages from each peer.
      Message types could be of type COMMIT, REVEAL, RESULT, BLOCK_PROPOSAL, etc. and each are handled accordingly.

### Assumptions 
To simplify our blockchain implementation, we have made the following assumptions
  1. All peers have joined before the first match starts. This means that each instance of peer.py must be started immediately and consecutively. This is crucial because if a peer joins too late, it will simply reject all "BLOCK_PROPOSAL" messages and therefore never add to its local chain.
  2. When a peer has detected forking, it may drop a few blocks.


### Blockchain
### Our Commit and Reveal Scheme
- In each match, players must send their direct opponent other a commit and reveal message to lock in their move. The commit message contains a hash of their move + randomized key. The reveal message contains the move + randomized key used to generate that hash. Once both commits and both reveals are stored in a player's local transaction buffer, the result is decided and also appended. This scheme ensures that cheating does not occur while playing the game. 
- Hence, each block contains a transaction containing two commits, two reveals, and one result.
- The player with the lower peer id gets assigned to mine the block. Whoever mines first broadcasts their block to all all peers through a "BLOCK_PROPOSAL" message. The player also adds the mined block to its local chain. 
- Peers who have received a "BLOCK_PROPSOAL" message verify the block's validity and add it to their own local chain.
- To deal with the collision of "BLOCK_PROPOSAL" messages, we've implemented states where a miner is not allowed to broadcast their block if another peer has broadcasted before them. If this is the case, they add their mined block to a pending list that will be re-mined and re-broadcasted at a later time.

### Dealing with Forking
-  Say miner #1 and miner #2 finish mining at the same time, they both broadcast a proposal for block #1 to all peers and append their mined block to their own local chain. When all peers receive the first proposal for block #1, they append to their local chains. When they receive the second proposal for block #1, they detect that forking has occurred and keep whichever block has the better PoW. PoW is determined by comparing the blocks header hash values. The block with the worst PoW is discarded, so all peers (including miners) have the same block #1 on their local blockchain. Finally, miner #3 finishes mining but because it already received a block proposal message, it appends it to a list of blocks to be re-mined and broadcasted in the future. If we let the matches continue, all local blockchains are in sync.

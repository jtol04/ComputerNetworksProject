# Rock Paper Scissors Blockchain App
Final Project - Computer Networks W4119


## Project Structure

An overview of the project's files and directories with brief descriptions:

```plaintext
├── templates/                # HTML templates
│   └── whiteboard.html
├── app.py                    # Flask application entry point for the UI
├── blockchain.py             # Core blockchain logic: Block, Chain, mining, and validation
├── DESIGN.md                 # Project design documentation and architecture diagrams
├── global_vars.py
├── peer.py                   # Peer node logic: commit-reveal protocol, peer-communication
├── README.md                 # Project overview, setup instructions, and usage guide
├── TESTING.md                # Testing strategy, manual & automated tests, and scenarios
├── tracker.py                # Tracker server: handles new peers/matchmaking
└── utils.py                  # Helper functions: hashing, proof‑of‑work checks...
```

### Running the tracker
`python ./tracker.py`

### Running peers (one per terminal)
`python ./peer.py`

(Btw, it is incredibly crucial that all peer instances are ready before a match starts. Part of our assumptions is that N peers must have joined the server before the first match. This can be done by having split terminals on VS Code)

### Running local UI website
`python ./app.py`

:) Axel, Jary, Srujan, Nate
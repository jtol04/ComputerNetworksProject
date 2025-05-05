# Testing

This document outlines the testing strategy for our Rock, Paper, Scissors Blockchain application. It covers manual, integration, and automated tests, style compliance checks, and our incremental testing strategy we used when developing this program.

---

## 1. Prerequisites

* **Python:** 3.7 or newer

Install required packages:

```bash
pip install -r requirements.txt
```

---

## 2. Manual Testing

### 2.1. Tracker Server

1. Start the tracker:

   ```bash
   python3 tracker.py
   ```
2. Verify console output indicates the tracker is listening on port 9000.
3. In another terminal, fetch known chains:

   ```bash
   curl http://localhost:9000/chains
   ```
4. Expect a JSON response with one or more blockchains (arrays of blocks).

### 2.2. Peer Nodes

1. With the tracker running, start multiple peers:

   ```bash
   python3 peer.py
   ```
2. Each peer should bind to a random port, print its game port, and register with the tracker.
3. Observe that peers are matched into games (commit phase) and then complete reveal/results.
4. Check console logs for:

   * Commit and reveal messages
   * Blockchain updates (mined blocks) on each peer
5. Confirm that no peer accepts an invalid reveal (mismatched hash).

### 2.3. Web UI (Whiteboard.html)

1. Start the Flask app:

   ```bash
   python3 app.py
   ```
2. Open a browser and navigate to [http://localhost:8000/](http://localhost:8000/)
3. Confirm the whiteboard page loads without errors.
4. Refresh accordinly and ensure it displays the current chains fetched from the tracker.

---

## 3. Unit Tests


### 3.1. Blockchain Module

* Test Block.header() returns a dict matching the instance fields.
* Test Block.header\_hash() matches the SHA256 of the header JSON.
* Test Block.mine() finds a nonce satisfying pow\_ok().
* Test Block.to\_json() and Block.from\_json() round-trip.

### 3.2. Utils Module

* Test sha256() produces correct hashes for known inputs.
* Test hash\_json() produces identical hashes for equivalent dicts.
* Test pow\_ok() returns True for valid hashes and False otherwise.

### 3.3. Peer Logic

* Test commit–reveal flow by mocking sockets or running two peer instances in a test harness.
* Use threading and socketpair to simulate peer-to-peer messages.

---

## 4. Integration Tests

Combine tracker, peers, and UI:

1. Launch tracker in background.
2. Spawn 3 peers.
3. Wait for a full game cycle (commit → reveal → result).
4. Query each peer’s blockchain via its local data structures or via tracker to confirm all blocks are consistent.

---

## 5. Style and Documentation Compliance

### 5.1. PEP 8 Compliance

Run flake8 at the project root:

```bash
flake8 .
```

* Fix any reported errors or warnings (line length, import ordering, unused imports, indentation).

### 5.2. Docstring Validation

Enforce multi-line docstrings for all modules, classes, and public methods with pydocstyle:

```bash
pydocstyle .
```

* Ensure every module starts with a descriptive docstring.
* Each class and public method/function has a multi-line docstring (triple-quoted).

---

## 6. Concurrency and Robustness Tests

* Introduce fake network delays or dropped messages to simulate unreliable networks.
* Verify that peers recover from missed messages and that the blockchain remains consistent.
* Test simultaneous commit broadcasts to ensure forks are handled or prevented according to design requirements.

---

## 7. Edge Case and Error Handling Tests

* Attempt to reveal with incorrect nonce/key; expect the logic to reject the transaction.
* Startup peers when tracker is down; peers should handle connection failures gracefully (retry or exit with informative message).
* Submit an empty or malformed transaction; expect clear error logs and no crash.

---

## 8. Tests + Expected Results

### 8.1. Two-Peer Scenario

**Setup:**

1. Start tracker:

   ```bash
   python3 tracker.py
   ```
2. Launch exactly two peers in separate terminals:

   ```bash
   python3 peer.py
   python3 peer.py
   ```
3. (Optional) Start the UI:

   ```bash
   python3 app.py
   ```

**Expected Behavior & Output:**

* **Tracker Console:** Should log two peer registrations and match them into a single game.
* **Peer Consoles:**

  * Both peers print commit and reveal messages.
  * After reveal, both peers append two new blocks (commit block + reveal block) to their chains.
  * Final console line shows game result (win/lose/tie).
* **UI (Whiteboard):**

  * Displays exactly one match with two players.
  * Shows commit phase indicator, then reveal phase, then outcome message.

### 8.2. Three-Peer Scenario

**Setup:**

1. Start tracker.
2. Launch three peers:

   ```bash
   python3 peer.py & python3 peer.py & python3 peer.py
   ```

**Expected Behavior & Output:**

* **Tracker Console:** Logs three peer registrations; pairs the first two peers into a game, leaving the third waiting.
* **Peer Consoles:**

  * Peers 1 & 2 execute commit → reveal → result, appending two blocks each.
  * Peer 3 stays registered but does not enter a match until another peer registers.
* **UI:**

  * One completed match displayed (players 1 & 2).
  * An indicator or placeholder for the waiting third peer.

### 8.3. Fork of length Depth-1 Scenario

**Setup:**

1. Start tracker.
2. Launch two peers but block network communication right after their commit phase (simulate delay).
3. Allow each peer to mine a commit block locally (fork depth 1).
4. After a short delay, allow one peer’s commit block to propagate, then let the second peer mine another block (fork depth 2).

**Expected Behavior & Output:**

* **Local Chains:**

  * Peer A chain: genesis → commitA → commitB
  * Peer B chain: genesis → commitB → commitA
* **Tracker/Network Logs:**

  * Detects two competing branches of length 2.
* **Resolution:**

  * Upon full propagation, the longer or higher-difficulty chain is adopted by both peers (depending on consensus rule).

---

*Last updated: May 5, 2025*

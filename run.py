import subprocess
import time
import os
import threading
import json
import socket

def kill_process_on_port(port):
    """Kill any process running on the specified port"""
    try:
        result = subprocess.run(["lsof", "-i", f":{port}"], capture_output=True, text=True)
        lines = result.stdout.splitlines()
        if len(lines) > 1:
            pid = lines[1].split()[1]
            os.system(f"kill -9 {pid}")
            print(f"🛑 Killed process on port {port}")
    except Exception as e:
        print(f"Error killing process on port {port}: {e}")

def print_blockchain_periodically(miner_address, interval=5):
    """Periodically fetch and display the blockchain state"""
    while True:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(miner_address)
                s.send(json.dumps({"type": "get_blockchain"}).encode())
                response = json.loads(s.recv(4096).decode())
                if "blockchain" in response:
                    print("\n=== Current Blockchain ===")
                    for block in json.loads(response["blockchain"]):
                        print(f"Block {block['index']}:")
                        print(f"  Hash: {block['hash']}")
                        print(f"  Previous Hash: {block['previous_hash']}")
                        print(f"  Votes: {len(block['votes'])} transactions")
                    print("=========================\n")
        except Exception as e:
            print(f"Error fetching blockchain: {e}")
        time.sleep(interval)

def register_nodes():
    """Register all miner nodes with each other"""
    miners = [("127.0.0.1", 6001), ("127.0.0.1", 6002), ("127.0.0.1", 6003)]
    for i, miner in enumerate(miners):
        other_miners = [f"http://{m[0]}:{m[1]}" for j, m in enumerate(miners) if j != i]
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(miner)
                s.send(json.dumps({
                    "type": "nodes/register",
                    "nodes": other_miners
                }).encode())
                response = json.loads(s.recv(4096).decode())
                print(f"Registered nodes with miner {miner[1]}: {response.get('message')}")
        except Exception as e:
            print(f"Error registering nodes with miner {miner[1]}: {e}")

def run_system():
    """Main function to run the entire system"""
    # Kill any existing processes
    kill_process_on_port(5001)  # TP1
    kill_process_on_port(5002)  # TP2
    kill_process_on_port(6001)  # Miner 1
    kill_process_on_port(6002)  # Miner 2
    kill_process_on_port(6003)  # Miner 3

    # Define all processes to start
    processes = [
        # Trusted Parties
        ["python", "tp1.py"],
        ["python", "tp2.py"],
        
        # Miners
        ["python", "pow.py", "--port", "6001"],
        ["python", "pow.py", "--port", "6002"],
        ["python", "pow.py", "--port", "6003"],
        
        # Wait for miners to initialize
        ["sleep", "10"],
        
        # # Register nodes
        # ["python", "-c", "from script import register_nodes; register_nodes()"],
        
        # Voters
        *[["python", "voter.py", "--voter", str(i), "--candidate", "Candidate" + ("A" if i%2 else "B")] 
          for i in range(1, 13)],

        ['bash', 'mine&resolve.sh']

        *[["python", "voter.py", "--voter", str(i), "--candidate", "Candidate" + ("A" if i%2 else "B")] 
          for i in range(13, 19)],

        ['bash', 'mine&resolve.sh']
    ]
    
    # Start all processes
    procs = []
    try:
        print("🚀 Starting Blockchain Voting System...")
        for cmd in processes:
            if cmd[0] == "sleep":
                time.sleep(int(cmd[1]))
            else:
                p = subprocess.Popen(cmd)
                procs.append(p)
                print(f"Started: {' '.join(cmd)}")

        # Start blockchain monitoring
        monitor = threading.Thread(
            target=print_blockchain_periodically,
            args=(("127.0.0.1", 6001),),
            daemon=True
        )
        monitor.start()

        # register_nodes()

        # Keep running until interrupted
        while True:
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n🛑 Shutting down system...")
        for p in procs:
            p.terminate()

def register_nodes():
    """Register all miner nodes with each other"""
    miners = [("127.0.0.1", 6001), ("127.0.0.1", 6002), ("127.0.0.1", 6003)]
    for i, miner in enumerate(miners):
        other_miners = [f"http://{m[0]}:{m[1]}" for j, m in enumerate(miners) if j != i]
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.connect(miner)
                s.send(json.dumps({
                    "type": "nodes/register",
                    "nodes": other_miners
                }).encode())
                response = json.loads(s.recv(4096).decode())
                print(f"Registered nodes with miner {miner[1]}: {response.get('message')}")
        except Exception as e:
            print(f"Error registering nodes with miner {miner[1]}: {e}")

if __name__ == "__main__":
    run_system()

# curl -X POST -H "Content-Type: application/json" -d '{"nodes": ["http://127.0.0.1:6002", "http://127.0.0.1:6001"] }' "http://127.0.0.1:6003/nodes/register"
# curl "http://127.0.0.1:6003/nodes/resolve"
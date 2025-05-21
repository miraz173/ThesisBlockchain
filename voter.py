import socket
import json
import random
import time
import hashlib
from Crypto.Hash import SHA256
import argparse

class Voter:
    def __init__(self, voter_id, candidate_id, miner_addresses, m):
        self.voter_id = voter_id
        self.candidate_id = candidate_id
        self.miner_addresses = miner_addresses
        self.m = m
        self.encrypted_vote = None
        self.unblinded_signed_hash = None
        # self.vote_id = None
        self.signer_id = None
        
        try:
            self.encrypted_vote = self.request_encryption()
            self.unblinded_signed_hash = self.request_blind_signature()
            print(self.signer_id)
            # self.vote_id = self.generate_vote_id()
            self.broadcast_vote()
            self.confirm_vote_inclusion()
        except Exception as e:
            print(f"❌ Voting failed for {voter_id}: {str(e)}")

    def request_encryption(self):
        """Request vote encryption from TP1"""
        message = json.dumps({
            "voter_id": self.voter_id,
            "candidate": self.candidate_id,
            "timestamp": time.time()
        })
        response = self.send_request("127.0.0.1", 5001, {
            "type": "encrypt_vote",
            "message": message
        })
        return bytes.fromhex(response["encrypted_vote"])

    def request_blind_signature(self):
        """Request blind signature from TP2"""
        hash_obj = SHA256.new(self.encrypted_vote)
        response = self.send_request("127.0.0.1", 5002, {
            "type": "blind_sign",
            "hash": hash_obj.hexdigest()
        })
        # print(response)
        self.signer_id=response["signerID"]#added
        return response["signature"]
        # return response["signature"], response["signerID"] #pass both signature and signerId

    def generate_vote_id(self):
        """Generate unique vote ID"""
        return hashlib.sha256(
            f"{self.encrypted_vote.hex()}{self.unblinded_signed_hash}".encode()
        ).hexdigest()

    def broadcast_vote(self):
        """Send vote to multiple miners"""
        vote_package = {
            # "vote_id": self.vote_id,
            "signer_id": self.signer_id,
            "encrypted_vote": self.encrypted_vote.hex(),
            "signed_hash": self.unblinded_signed_hash
        }
        
        successes = 0
        for miner in random.sample(self.miner_addresses, len(self.miner_addresses)):
            try:
                response = self.send_flask_request(miner[0], miner[1], {
                    "type": "add_vote",
                    "vote": vote_package
                })
                if response.get("status") == "received":
                    successes += 1
                    if successes >= self.m:
                        print(f"✅ Vote from {self.voter_id} accepted by {self.m} miners")
                        return True
            except Exception as e:
                print(f"⚠️ Couldn't reach miner {miner}: {e}")
        
        raise Exception(f"Only reached {successes}/{self.m} required miners")

    def confirm_vote_inclusion(self):
        """Check if vote was included in blockchain"""
        print(f"🔍 {self.voter_id} checking for vote inclusion...")
        start_time = time.time()
        timeout = 120  # 2 minute timeout
        
        while time.time() - start_time < timeout:
            for miner in self.miner_addresses:
                try:
                    chain = self.send_flask_request(miner[0], miner[1], {
                        "type": "get_blockchain"
                    })
                    # print(f"voter- {self.voter_id} received: {chain['blockchain']}")#comment out
                    for block in json.loads(chain["blockchain"]):
                        for vote in block.get("votes", []):
                            # if vote.get("vote_id") == self.vote_id:
                            if vote.get("signed_hash") == self.unblinded_signed_hash:
                                print(f"✅ {self.voter_id} vote confirmed in block {block['index']}")
                                return True
                except Exception:
                    continue
            
            time.sleep(5)  # Check every 5 seconds
        
        raise Exception(f"Vote not found in blockchain after {timeout} seconds")

    def send_request(self, host, port, data):
        """Generic request sender"""
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.settimeout(5)
            s.connect((host, port))
            s.sendall(json.dumps(data).encode())
            return json.loads(s.recv(8192).decode())
        
    def send_flask_request(self, host, port, data):
        """Send properly formatted HTTP request"""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(5)
                s.connect((host, port))
                
                if data.get("type") == "add_vote":
                    x=f"POST /vote/add HTTP/1.1\r\n"
                elif data.get("type") == "get_blockchain":
                    x=f"GET /get_blockchain HTTP/1.1\r\n"
                else:
                    x=f"POST /vote/new HTTP/1.1\r\n"
                # Format as proper HTTP request
                http_request = (
                    x+
                    f"Host: {host}:{port}\r\n"
                    f"Content-Type: application/json\r\n"
                    f"Content-Length: {len(json.dumps(data))}\r\n"
                    f"\r\n"
                    f"{json.dumps(data)}"
                )
                
                s.sendall(http_request.encode())
                
                # Read HTTP response
                response = b""
                while True:
                    chunk = s.recv(4096)
                    if not chunk:
                        break
                    response += chunk
                
                # Extract JSON from HTTP response
                header, _, body = response.partition(b"\r\n\r\n")
                s.close()#added, confusion
                return json.loads(body.decode())
                
        except Exception as e:
            print(f"Network error: {str(e)}")
            raise

def main():
    parser = argparse.ArgumentParser(description="Run a voter node")
    parser.add_argument("--voter", type=int, required=True, help="Voter ID number")
    parser.add_argument("--candidate", type=str, required=True, help="Candidate name")
    
    args = parser.parse_args()
    
    # Configure miner nodes
    miners = [("127.0.0.1", 6001), ("127.0.0.1", 6002), ("127.0.0.1", 6003)]
    min_confirmations = 2  # Require 2 miner confirmations
    
    # Create and run voter
    Voter(
        voter_id=f"Voter{args.voter}",
        candidate_id=args.candidate,
        miner_addresses=miners,
        m=min_confirmations
    )

if __name__ == "__main__":
    main()
import socket
import json
import random
from Crypto.PublicKey import RSA

class TP2Server:
    def __init__(self):
        self.key = RSA.generate(2048)
        self.public_key = self.key.publickey()
        self.signerID = 33#random.random(2)#signerID added later

    def handle_request(self, data):
        try:
            request = json.loads(data)
            if request["type"] == "blind_sign":
                hash_int = int(request["hash"], 16)
                blinding_factor = random.randint(2, self.key.n - 1)
                blinded = (hash_int * pow(blinding_factor, self.public_key.e, self.key.n)) % self.key.n
                blinded_sig = pow(blinded, self.key.d, self.key.n)
                unblinded_sig = (blinded_sig * pow(blinding_factor, -1, self.key.n)) % self.key.n
                return {"signature": unblinded_sig, "signerID": self.signerID}#signerID added extra
            return {"error": "Invalid request type"}
        except Exception as e:
            return {"error": str(e)}

    def run(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("127.0.0.1", 5002))
        server.listen(5)
        print("✍️ TP2 Blind Signing Service running on port 5002")
        
        while True:
            client, addr = server.accept()
            try:
                data = client.recv(4096).decode()
                response = self.handle_request(data)
                client.send(json.dumps(response).encode())
            except Exception as e:
                client.send(json.dumps({"error": str(e)}).encode())
            finally:
                client.close()

if __name__ == "__main__":
    TP2Server().run()
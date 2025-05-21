import socket
import json
from Crypto.PublicKey import RSA
from Crypto.Cipher import PKCS1_OAEP

class TP1Server:
    def __init__(self):
        self.key = RSA.generate(2048)
        self.public_key = self.key.publickey()
        self.cipher = PKCS1_OAEP.new(self.key)

    def handle_request(self, data):
        try:
            request = json.loads(data)
            if request["type"] == "encrypt_vote":
                encrypted = self.cipher.encrypt(request["message"].encode())
                return {"encrypted_vote": encrypted.hex()}
            return {"error": "Invalid request type"}
        except Exception as e:
            return {"error": str(e)}

    def run(self):
        server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server.bind(("127.0.0.1", 5001))
        server.listen(5)
        print("🔒 TP1 Encryption Service running on port 5001")
        
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
    TP1Server().run()
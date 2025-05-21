import hashlib
import json
from time import time
from urllib.parse import urlparse
from uuid import uuid4

import requests
from flask import Flask, jsonify, request


class Blockchain:
    def __init__(self):
        self.pending_votes = []
        self.chain = []
        # self.nodes = set()
        self.nodes = {"127.0.0.1:6003", "127.0.0.1:6002", "127.0.0.1:6001"}
        self.new_block(previous_hash='1', nonce=100)

    def new_block(self, nonce, previous_hash):
        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'votes': self.pending_votes[:4], #first 4 votes
            'nonce': nonce,
            'previous_hash': self.hash(self.chain[-1]) if self.chain else previous_hash,
        }

        block_hash=self.hash(block)
        while block_hash[:4] != "0000":
            block['nonce'] += 1
            block_hash = self.hash(block)

        self.pending_votes = self.pending_votes[4:]  # Remove the first 4 votes
        self.chain.append(block)
        return block
    
    def register_node(self, address):
        parsed_url = urlparse(address)
        if parsed_url.netloc:
            self.nodes.add(parsed_url.netloc)
        elif parsed_url.path:
            self.nodes.add(parsed_url.path)
        else:
            raise ValueError('Invalid URL')

    def valid_chain(self, chain):
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            last_block_hash = self.hash(last_block)

            if block['previous_hash'] != last_block_hash:
                print(f"Invalid previous hash at block {current_index}")
                return False
            if self.hash(block)[:4] != "0000":
                print(f"Invalid proof of work at block {current_index}")
                return False
            if block['timestamp'] <= last_block['timestamp']:
                print(f"Invalid timestamp at block {current_index}")
                return False
            
            last_block = block
            current_index += 1
        print("\nValid chain at node {self.nodes}\n")
        return True

    def resolve_conflicts(self):
        neighbours = self.nodes
        new_chain = None

        max_length = len(self.chain)
        print(neighbours)
        for node in neighbours:
            response = requests.get(f'http://{node}/chain')
            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']

                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        if new_chain:
            self.chain = new_chain
            return True

        return False

    def new_vote(self, vote):
        # Validate vote structure
        # required_fields = ['vote_id', 'encrypted_vote', 'signed_hash']
        required_fields = ['signer_id', 'encrypted_vote', 'signed_hash']
        if not all(field in vote for field in required_fields):
            raise ValueError('Invalid vote format')
        
        self.pending_votes.append(vote)
        return self.last_block['index'] + 1

    @property
    def last_block(self):
        return self.chain[-1]

    @staticmethod
    def hash(block):
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    #unneded
    def proof_of_work(self, last_block):
        last_nonce = last_block['nonce']
        last_hash = self.hash(last_block)

        nonce = 0
        while not self.valid_proof(last_nonce, nonce, last_hash):
            nonce += 1

        return nonce

    @staticmethod #unneded
    def valid_proof(last_nonce, nonce, last_hash):
        guess = f'{last_nonce}{nonce}{last_hash}'.encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"


app = Flask(__name__)

node_identifier = str(uuid4()).replace('-', '')

blockchain = Blockchain()


@app.route('/mine', methods=['GET'])
def mine():
    if len(blockchain.pending_votes) < 4:
        return jsonify({'message': 'Not enough votes to mine'}), 400
    
    last_block = blockchain.last_block
    nonce = blockchain.proof_of_work(last_block)

    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(nonce, previous_hash)#pow needs complete overhaul

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'timestamp': block['timestamp'],
        'votes': len(block['votes']),
        'nonce': block['nonce'],
        'previous_hash': block['previous_hash'][:7],
        'hash': blockchain.hash(block)[:7],
    }
    return jsonify(response), 200


@app.route('/vote/new', methods=['POST'])
def new_vote(values):#add_vote passes (vote_data), which is actual content of vote field
    # values = request.get_json()
    # values = values.get('vote')
    # required = ['vote_id', 'encrypted_vote', 'signed_hash']
    required = ['signer_id', 'encrypted_vote', 'signed_hash']
    if not all(k in values for k in required):
        return 'Missing vote data', 400

    index = blockchain.last_block()
    return jsonify({'message': f'Vote will be added to Block {index}'}), 201


@app.route('/vote/add', methods=['POST'])
def add_vote():
    values = request.get_json()
    
    # Handle both formats
    if 'type' in values and values['type'] == 'add_vote':
        vote_data = values.get('vote')
    else:
        vote_data = values.get('vote')
    
    if not vote_data:
        print("no vote data")
        return jsonify({'status': 'error', 'message': 'No vote data provided'}), 406
    
    try:
        resp=blockchain.new_vote(vote_data)
        print(f"vote will be added on block {resp}")
        return jsonify({'status': 'received'}), 201
    except Exception as e:
        print(f"Error adding vote: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 407


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200


@app.route('/get_blockchain', methods=['GET', 'POST'])
def get_blockchain():
    chain_data = blockchain.chain
    return jsonify({"blockchain": json.dumps(chain_data)}), 200


@app.route('/nodes/register', methods=['POST'])
def register_nodes():
    values = request.get_json()
    nodes = values.get('nodes')
    if nodes is None:
        return "Error: Please supply a valid list of nodes", 400

    for node in nodes:
        blockchain.register_node(node)

    response = {
        'message': 'New nodes have been added',
        'total_nodes': list(blockchain.nodes),
    }
    return jsonify(response), 201


@app.route('/nodes/resolve', methods=['GET'])
def consensus():
    replaced = blockchain.resolve_conflicts()

    if replaced:
        response = {
            'message': 'Our chain was replaced',
            'new_chain length': len(blockchain.chain),
            'time': blockchain.chain[-1]['timestamp'],
        }
    else:
        response = {
            'message': 'Our chain is authoritative',
            'chain length': len(blockchain.chain),
            'time': blockchain.chain[-1]['timestamp'],
        }

    return jsonify(response), 200


if __name__ == '__main__':
    from argparse import ArgumentParser

    parser = ArgumentParser()
    parser.add_argument('-p', '--port', default=6001, type=int, help='port to listen on')
    args = parser.parse_args()
    port = args.port

    app.run(host='0.0.0.0', port=port)

    # blockchain.nodes={"127.0.0.1:6001","127.0.0.1:6002","127.0.0.1:6003","127.0.0.1:6004"}
    # while blockchain.chain == []:
    #     print("Waiting for the genesis block...")
    #     time.sleep(1)
    
    # while True:
    #     while len(blockchain.pending_votes)>=4:
    #         print("Mining...")
    #         last_block = blockchain.last_block
    #         nonce = blockchain.proof_of_work(last_block)

    #         previous_hash = blockchain.hash(last_block)
    #         block = blockchain.new_block(nonce, previous_hash)#pow needs complete overhaul

    #         response = {
    #             'message': "New Block Forged",
    #             'index': block['index'],
    #             'timestamp': block['timestamp'],
    #             'votes': block['votes'][:7],
    #             'nonce': block['nonce'],
    #             'previous_hash': block['previous_hash'][:7],
    #             'hash': blockchain.hash(block)[:7],
    #         }
    #         print(response)
    #         time.sleep(5)

    #         try:
    #             print("Resolving conflicts...")
    #             blockchain.resolve_conflicts()
    #         except Exception as e:
    #             print(f"Error resolving conflicts: {e}")
    #         time.sleep(10)

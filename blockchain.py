import hashlib
import json
from textwrap import dedent
from time import time
from uuid import uuid4

from flask import Flask, jsonify, request
from urllib.parse import urlparse


class BlockChain(object):
    def __init__(self):
        self.chain = []
        self.current_transactions = []
        self.nodes = set()

        # create genesys block
        self.new_block(previous_hash=1, proof=100)

    def register_node(self, address):
        """
        Add a new node to the list of nodes
        :param address: <str> Address of node. Eg 'http://192.168.0.5:5000'
        :return: None
        """

        parsed_url = urlparse(address)
        self.nodes.add(parsed_url.netloc)

    def valid_chain(self, chain):
        """
        Check if given blockchain is valid
        :param chain: <list> a blockchain
        :return: <bool> True if valid, False if not
        """
        last_block = chain[0]
        current_index = 1

        while current_index < len(chain):
            block = chain[current_index]
            print ("Last block - {}".format(last_block))
            print ("Block - {}".format(block))
            print ("\n=============\n")

            # Check that the Proof
            if block['previous_hash'] != self.hash(last_block):
                return False

            # Chack if Proof of Work is correct
            if not self.valid_proof(last_block['proof'], block['proof']):
                return False

            last_block = block
            current_index += 1

        return True

    def resolve_coflicts(self):
        """
        Consensus algoritm, resolves conflicts by replacing our
        chain with the longest one in the netWork
        :return: <bool> True if our chain was replaced, else False
        """

        neighbors = self.nodes
        new_chain = None

        # Looking for  chains that`s Only longer than ours
        max_length = None

        # Grab & verify the chains from all nodes in our netWork

        for node in neighbors:
            response = request.get("http://{0}/chain".format(node))

            if response.status_code == 200:
                length = response.json()['length']
                chain = response.json()['chain']


                # Check if len is longer and valid
                if length > max_length and self.valid_chain(chain):
                    max_length = length
                    new_chain = chain

        # Replace our chain if discovered longer & valid chain
        if new_chain:
            self.chain = new_chain
            return True
        return False

    def new_block(self, proof, previous_hash=None):
        """
        Creates a new block and adds it to the chain
        :param proof: <int> The proof given by Proof of Work algoritm
        :param previous_hash: (Optional) <str> Hash of previous Block
        :return: <dict> New Block
        """

        block = {
            'index': len(self.chain) + 1,
            'timestamp': time(),
            'transactions': self.current_transactions,
            'proof': proof,
            'previous_hash': previous_hash or self.hash(self.chain[-1])
        }

        # Reset the current list of transactions
        self.current_transactions = []

        self.chain.append(block)
        return block

    def new_transaction(self, sender, recipient, amount):
        '''
        Adds a new transaction to the list of transactions
        :param sender: <str> Address of the Sender
        :param recipient: <str> Address of the Recipient
        :param amount: <str> Amount
        :return: <int> The index of Block that will hold this transaction

        '''
        self.current_transactions.append({
            'sender': sender,
            'recipient': recipient,
            'amount': amount
        })

        return self.last_block['index'] + 1

    def proof_of_work(self, last_proof):
        """
        Simple Proof of Work Algorithm

            - Find a number p' such that hash (pp') contains 4 leading zeroes,
            where p is the previous p'
            - p is the previous proof, and p' is the new proof

        :param last_proof: <int>
        :return: <int>
        """

        proof = 0
        while self.valid_proof(last_proof, proof) is False:
            proof += 1

        return proof

    @staticmethod
    def valid_proof(last_proof, proof):
        """
        Validates Proof: Does hash(last_proof, proof) contain 4 leading zeroes?

        :param last_proof: <int> Previous Proof
        :param proof: <int> Current Proof
        :return: <bool> True if correct, False if not
        """
        guess = "{0}{1}".format(last_proof, proof).encode()
        guess_hash = hashlib.sha256(guess).hexdigest()
        return guess_hash[:4] == "0000"

    @staticmethod
    def hash(block):
        """
        Creates a SHA-256 hash of a Block

        :param block: <dict> Block
        :return: <str>
        """

        # Must ensure that the Dictionary is ordered, or we`ll have inconsistent hashes
        block_string = json.dumps(block, sort_keys=True).encode()
        return hashlib.sha256(block_string).hexdigest()

    @property
    def last_block(self):
        # returns the last block in the chain
        return self.chain[-1]


# Node Initiation with FLASK
app = Flask(__name__)

# gener global unique address for node
node_identifier = str(uuid4()).replace('-', '')

# init a blockChain
blockchain = BlockChain()


@app.route('/mine', methods=['GET'])
def mine():
    # We run the proof of work algorithm to get new proof
    last_block = blockchain.last_block
    last_proof = last_block['proof']

    proof = blockchain.proof_of_work(last_proof)

    # We must receive a reward for finding the proof.
    # The sender is "0" to signify that this node has mined a new coin
    blockchain.new_transaction(
        sender='0',
        recipient=node_identifier,
        amount=1,
    )

    # Forge the new Block by adding it to the chain
    previous_hash = blockchain.hash(last_block)
    block = blockchain.new_block(proof, previous_hash)

    response = {
        'message': "New Block Forged",
        'index': block['index'],
        'transactions': block['transactions'],
        'proof': block['proof'],
        "previous_hash": block['previous_hash'],
    }
    return jsonify(response), 200


@app.route('/transactions/new', methods=['POST'])
def new_transaction():
    # Add`s a new transaction"
    values = request.get_json()

    # Check that the required fields are in  POST`ed data
    required = ['sender', 'recipient', 'amount']
    if not all(k in values for k in required):
        return "Missing Values", 400

    # create a new Transaction
    index = blockchain.new_transaction(
        values['sender'],
        values['recipient'],
        values['amount'])

    response = {'message': "Transaction will be added to Block{}".format(index)}
    return jsonify(response), 201


@app.route('/chain', methods=['GET'])
def full_chain():
    response = {
        'chain': blockchain.chain,
        'length': len(blockchain.chain),
    }
    return jsonify(response), 200   # remove FLASK


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)

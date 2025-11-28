"""
This module contains the class Block. A block is a list of transactions. The first block is called the genesis block.
"""

import hashlib
import json
import config
import utils
from rich.console import Console
from rich.table import Table


class InvalidBlock(Exception):
    pass


class Block(object):
    def __init__(self, data=None):
        """
        If data is None, create a new genesis block. Otherwise, create a block from data (a dictionary).
        Raise InvalidBlock if the data are invalid.
        """
        self.index = 0
        self.timestamp = "2023-11-24 00:00:00.000000"
        self.transactions = []
        self.proof = 0
        self.previous_hash = "0" * 64 

    def next(self, transactions):
        """
        Create a block following the current block
        :param transactions: a list of transactions, i.e. a list of messages and their signatures
        :return: a new block
        """
        new_block = Block()
        new_block.index = self.index + 1
        new_block.transactions = transactions
        new_block.previous_hash = self.hash()
        new_block.timestamp = utils.get_time()
        new_block.proof = 0
        return new_block

    def hash(self):
        """
        Hash the current block (SHA256). The dictionary representing the block is sorted to ensure the same hash for
        two identical block. The transactions are part of the block and are not sorted.
        :return: a string representing the hash of the block
        """
        block_dict = {
            "index": self.index,
            "timestamp": self.timestamp,
            "transactions": [t.data for t in self.transactions],
            "proof": self.proof,
            "previous_hash": self.previous_hash
        }
        block_string = json.dumps(block_dict, sort_keys=True)
        return hashlib.sha256(block_string.encode()).hexdigest()

    def __str__(self):
        """
        String representation of the block
        :return: str
        """
        return f"Block(index={self.index}, timestamp={self.timestamp}, transactions={len(self.transactions)}, proof={self.proof}, previous_hash={self.previous_hash})"

    def valid_proof(self, difficulty=config.default_difficulty):
        """
        Check if the proof of work is valid. The proof of work is valid if the hash of the block starts with a number
        of 0 equal to difficulty.

        If index is 0, the proof of work is valid.
        :param difficulty: the number of 0 the hash must start with
        :return: True or False
        """
        if self.index == 0:
            return True
        prefix = '0' * difficulty
        return self.hash().startswith(prefix)

    def mine(self, difficulty=config.default_difficulty):
        """
        Mine the current block. The block is valid if the hash of the block starts with a number of 0 equal to
        config.default_difficulty.
        :return: the proof of work
        """
        prefix = '0' * difficulty
        while not self.hash().startswith(prefix):
            self.proof += 1
        return self.proof

    def validity(self):
        """
        Check if the block is valid. A block is valid if it is a genesis block or if:
        - the proof of work is valid
        - the transactions are valid
        - the number of transactions is in [0, config.blocksize]
        :return: True or False
        """
        if self.index == 0:
            return True

        if not self.valid_proof():
            return False

        if not (0 <= len(self.transactions) <= config.blocksize):
            return False

        for t in self.transactions:
            if not t.verify():
                return False

        return True

    def log(self):
        """
        A nice log of the block
        :return: None
        """
        table = Table(
            title=f"Block #{self.index} -- {self.hash()[:7]}...{self.hash()[-7:]} -> {self.previous_hash[:7]}...{self.previous_hash[-7:]}")
        table.add_column("Author", justify="right", style="cyan")
        table.add_column("Message", style="magenta", min_width=30)
        table.add_column("Date", justify="center", style="green")

        for t in self.transactions:
            table.add_row(t.author[:7] + "..." + t.author[-7:], t.message, t.date[:-7])

        console = Console()
        console.print(table)


def test():
    from ecdsa import SigningKey
    from transaction import Transaction
    sk = SigningKey.generate()
    transactions = [Transaction(f"Message {i}") for i in range(10)]
    for t in transactions:
        t.sign(sk)

    Transaction.log(transactions)

    blocks = [Block()]
    for i in range(5):
        blocks.append(blocks[-1].next(transactions[i * 2:(i + 1) * 2]))
        blocks[-1].mine()

    for b in blocks:
        b.log()


if __name__ == '__main__':
    print("Test Block")
    test()

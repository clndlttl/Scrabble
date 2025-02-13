import logging
from logging.handlers import RotatingFileHandler
import time
import json

import pytrie
from redis import Redis

formatter = logging.Formatter('%(asctime)s %(levelname)-8s %(message)s')
formatter.converter = time.gmtime

logger = logging.getLogger('trie_logger')
logger.setLevel(logging.DEBUG)
handler = RotatingFileHandler('logs/trie.log', maxBytes=100000, backupCount=10)
handler.setFormatter(formatter)
logger.addHandler(handler)

# File path for storing the trie
WORDS_FILE = "enable.txt"

def build_trie_from_file(file_path):
    """
    Builds a trie from words stored in a text file.
    Each line in the file should contain one word.
    """
    trie = pytrie.StringTrie()
    try:
        with open(file_path, "r") as f:
            for line in f:
                word = line.strip()
                if word:  # Ignore empty lines
                    trie[word] = True  # Store True as a placeholder value
        logger.debug('Trie built from %s', file_path)
    except FileNotFoundError:
        logger.debug('Error: The file %s was not found.', file_path)
        raise
    return trie


class TrieSearcher:
    def __init__(self):
        self.bank = ''
        self.board = []
        self.trie = build_trie_from_file(WORDS_FILE)

    def isValid(self, word):
        rv = word in self.trie
        return str(rv)

    def makeMove(self, boardStr, bankStr):
        logger.debug('makeMove')

        self.bank = list(bankStr)
        self.board = []
        temp = boardStr.split('\n')
        for row in temp:
            self.board.append(list(row))

        '''
for each tile:
    if tile is a placed letter:

        for both horz and vertical:
        
        measure the gaps on either side
        if gap end is other placed letters (not board edge), note them as relational restrictions for words of at least that length.

        for both vert and horz, do a Depth-first traverse the trie using the current board letter and all bank letters.
        when a valid word is found, note it alongwith the grid idxs derived from the position of the current letter
        in the word. Score it, add the score to a list of tuples (score, [(r,c,'x'),(r,c,'x'),...])

sort the list by score, and then map the items to a pdf based on the "difficulty" setting.
choose a random move.
        '''

        return [(0,0,'c'),(0,1,'a'),(0,2,'t')]

if __name__ == '__main__':

    ts = TrieSearcher()

    r = Redis(host='localhost', port=6379, decode_responses=True)

    logger.debug("Waiting for messages...")

    while True:
        message = r.xread({'TrieChannel': '$'}, None, 0)
        
        cmd = message[0][1][0][1]
        
        if 'query' in cmd:
            word = cmd['query']
            logger.debug('Checking word: %s', word)
            result = ts.isValid(word)
            r.set(word, result)
        elif 'boardStr' in cmd and 'bankStr' in cmd:
            logger.debug('Making a move')
            move = ts.makeMove(cmd['boardStr'], cmd['bankStr'])
            rv = {'moveResponse': json.dumps(move)}
            r.xadd('TrieChannel', rv)
import pytrie
import pickle
import os

# File path for storing the trie
TRIE_FILE = "trie.pkl"
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
        print(f"Trie built from {file_path}.")
    except FileNotFoundError:
        print(f"Error: The file {file_path} was not found.")
        raise
    return trie

def load_or_create_trie(trie_file, words_file):
    """Loads the trie from a file, or creates and saves it if the file doesn't exist."""
    if os.path.exists(trie_file):
        print("Loading trie from disk...")
        with open(trie_file, "rb") as f:
            return pickle.load(f)
    else:
        print(f"Pickle file not found. Building a new trie from {words_file}...")
        trie = build_trie_from_file(words_file)
        with open(trie_file, "wb") as f:
            pickle.dump(trie, f)
        print("Trie saved to disk.")
        return trie

# Load or create the trie
trie = load_or_create_trie(TRIE_FILE, WORDS_FILE)

class TrieSearcher:
    def __init__(self, boardStr, bankStr, logger):
        self.logger = logger
        self.bank = list(bankStr)
        self.board = []
        temp = boardStr.split('\n')
        for row in temp:
            self.board.append(list(row))
    
    def makeMove(self):
        self.logger.debug('makeMove')

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

    
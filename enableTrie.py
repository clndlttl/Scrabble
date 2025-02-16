import logging
from logging.handlers import RotatingFileHandler
import time
import json
import random

import pytrie
from redis import Redis

from gameUtils import *

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


def dfs(node, path: list[str], letters_left: set[str], constraints: dict[int,str], minLength: int, results: set[str]):

    nextPosition = len(path)
    
    if node.value is True and minLength <= nextPosition :  # Found a valid word
        results.add(''.join(path))
    
    req = None
    if nextPosition in constraints:
        req = constraints[nextPosition]
    
    for char, child in node.children.items():
        if (char in letters_left and req is None) or (req == char):

            # Choose
            path.append(char)
            if not req:
                letters_left.remove(char)
            
            # Explore
            dfs(child, path, letters_left, constraints, minLength, results)
            
            # Un-choose (Backtrack)
            path.pop()
            if not req:
                letters_left.add(char)


class TrieSearcher:
    def __init__(self, redisObj):
        self.redis = redisObj
        self.trie = build_trie_from_file(WORDS_FILE)

    def validate(self, word: str) -> bool:
        isValid = word in self.trie
        if isValid:
            self.redis.set(word, '1')
        return isValid
    
    def scoreWords(self, words: dict[int, str]) -> int:
        '''
        words = {
            324: [('d',None),('o','.'),('g','#')], // this means 'd' was already played, and 'g' is double letter value
            135: [ ]
        }
        '''
        finalScore = 0
    
        seenHashes = set()
    
        for hash in words:
    
            if hash in seenHashes:
                continue
            
            seenHashes.add(hash)
    
            w = ''
            wordBonus = 1
            thisScore = 0
    
            for tup in words[hash]:
    
                letter = tup[0]
                space = tup[1]
    
                w += letter
    
                if space in [None,'.','*']:
                    thisScore += letterValues[letter]
                elif space == '#':
                    thisScore += letterValues[letter] * 2
                elif space == '@':
                    thisScore += letterValues[letter] * 3
                elif space == '%':
                    thisScore += letterValues[letter]
                    wordBonus *= 2
                elif space == '$':
                    thisScore += letterValues[letter]
                    wordBonus *= 3
    
            if not self.validate(w):
                finalScore = 0
                break
            else:
                finalScore += thisScore * wordBonus
    
        return finalScore


    def makeMove(self, boardStr: str, bankStr: str) -> None:
        logger.debug('makeMove...')

        bank = list(bankStr)
        N = len(bank)

        rowMajorBoard = []
        temp = boardStr.split('\n')
        for row in temp:
            rowMajorBoard.append(list(row))

        colMajorBoard = []
        for ci in range(15):
            nextColumn = [ rowMajorBoard[ri][ci] for ri in range(15) ]
            colMajorBoard.append(nextColumn)

        allMoves = []

        # Horizontal
        for ridx, row in enumerate(rowMajorBoard):
            prevIsLetter = False
            for cidx in range(15):

                if isLetter(row[cidx]):
                    if prevIsLetter:
                        continue
                    else:
                        prevIsLetter = True
                else:
                    prevIsLetter = False

                # See if we can touch a played tile within N spaces
                constraints = {}
                c = cidx
                numBank = N
                wordIdx = 0
                while (c < 15):
                    tile = row[c]
                    if isLetter(tile):
                        constraints[wordIdx] = tile
                    elif numBank == 0:
                        break
                    else:
                        numBank -= 1
                    c += 1
                    wordIdx += 1
                
                if len(constraints) == 0:
                    continue

                # need to enforce a minimum length
                sortedConstraintIdxs = sorted(constraints.keys())

                minLength = 0
                if sortedConstraintIdxs[0] == 0:
                    # starts with a placed letter: find the first blank space that is followed by a blank space
                    foundBlank = False
                    while True:
                        minLength += 1
                        if cidx+minLength == 15:
                            break
                        isBlank = minLength not in sortedConstraintIdxs
                        if isBlank:
                            if foundBlank:
                                # found two consecutive blanks!
                                break
                            else:
                                foundBlank = True
                        else:
                            foundBlank = False
                else:
                    # starts with a bank letter: find the first placed letter that is followed by a blank space 
                    foundPlaced = False
                    while True:
                        minLength += 1
                        if cidx+minLength == 15:
                            break
                        isPlaced = minLength in sortedConstraintIdxs
                        if foundPlaced and not isPlaced:
                            break
                        foundPlaced |= isPlaced
                
                if len(constraints) > 0:
                    # Find all possible words
                    possibleWords = set()
                    bankCopy = set(bank)
                    dfs(self.trie._root, [], bankCopy, constraints, minLength, possibleWords)
                   
                    pw = list(possibleWords)
                    for word in pw:
                        v = []
                        c = cidx
                        for letter in word:
                            if c >= 15:
                                break
                            # only include bank letters in move
                            if not isLetter(row[c]):
                                v.append( (ridx,c,letter) )
                            c += 1
                        allMoves.append(v)

        # Vertical
        for cidx, col in enumerate(colMajorBoard):
            prevIsLetter = False
            for ridx in range(15):

                if isLetter(col[ridx]):
                    if prevIsLetter:
                        continue
                    else:
                        prevIsLetter = True
                else:
                    prevIsLetter = False

                # See if we can touch a played tile within N spaces
                constraints = {}
                r = ridx
                numBank = N
                wordIdx = 0
                while ( r < 15):
                    tile = col[r]
                    if isLetter(tile):
                        constraints[wordIdx] = tile
                    elif numBank == 0:
                        break
                    else:
                        numBank -= 1
                    r += 1
                    wordIdx += 1
                
                if len(constraints) == 0:
                    continue

                # need to enforce a minimum length
                sortedConstraintIdxs = sorted(constraints.keys())

                minLength = 0
                if sortedConstraintIdxs[0] == 0:
                    # starts with a placed letter: find the first blank space that is followed by a blank space
                    foundBlank = False
                    while True:
                        minLength += 1
                        if ridx+minLength == 15:
                            break
                        isBlank = minLength not in sortedConstraintIdxs
                        if isBlank:
                            if foundBlank:
                                # found two consecutive blanks!
                                break
                            else:
                                foundBlank = True
                        else:
                            foundBlank = False
                else:
                    # starts with a bank letter: find the first placed letter that is followed by a blank space 
                    foundPlaced = False
                    while True:
                        minLength += 1
                        if ridx+minLength == 15:
                            break
                        isPlaced = minLength in sortedConstraintIdxs
                        if foundPlaced and not isPlaced:
                            break
                        foundPlaced |= isPlaced
                
                if len(constraints) > 0:
                    # Find all possible words
                    possibleWords = set()
                    bankCopy = set(bank)
                    dfs(self.trie._root, [], bankCopy, constraints, minLength, possibleWords)
                   
                    pw = list(possibleWords)
                    for word in pw:
                        v = []
                        r = ridx
                        for letter in word:
                            if r >= 15:
                                break
                            # only include bank letters in move
                            if not isLetter(col[r]):
                                v.append( (r,cidx,letter) )
                            r += 1
                        allMoves.append(v)

        hiScore = 0
        bestMoves = []
        for move in allMoves:
            errorList = []
            words, _, _ = findWords(rowMajorBoard, move, errorList)
            if len(errorList) == 0:
                score = self.scoreWords(words)
                if score > hiScore:
                    hiScore = score
                    bestMoves.clear()
                    bestMoves.append(move)
                elif score == hiScore:
                    bestMoves.append(move)

        if len(bestMoves) == 0:
            logger.debug('...move not found!')
            rv = {'moveResponse': json.dumps(None)}
        else:
            q = random.randint(0,len(bestMoves)-1)
            move = bestMoves[q]
            logger.debug('...Found move: %s', move)
            rv = {'moveResponse': json.dumps(move)}
        self.redis.xadd('TrieChannel', rv)


if __name__ == '__main__':

    
    r = Redis(host='localhost', port=6379, decode_responses=True)

    ts = TrieSearcher(r)
    
    logger.debug("Waiting for messages...")

    while True:
        message = r.xread({'TrieChannel': '$'}, None, 0)
        
        cmd = message[0][1][0][1]

        try:
        
            if 'query' in cmd:
                word = cmd['query']
                isValid = ts.validate(word)
                logger.debug('%s is %s', word, isValid)
            elif 'boardStr' in cmd and 'bankStr' in cmd:
                ts.makeMove(cmd['boardStr'], cmd['bankStr'])
        
        except Exception as e:
            logger.critical(str(e))


'''
    testBoard =  '...............\n'
    testBoard += '...............\n'
    testBoard += '...............\n'
    testBoard += '...............\n'
    testBoard += '...............\n'
    testBoard += '...............\n'
    testBoard += '...............\n'
    testBoard += '......cat......\n'
    testBoard += '...............\n'
    testBoard += '...............\n'
    testBoard += '...............\n'
    testBoard += '...............\n'
    testBoard += '...............\n'
    testBoard += '...............\n'
    testBoard += '...............'

    testBank = 'sedtion'

    bestMove = ts.makeMove(testBoard, testBank)
    print(bestMove)
'''
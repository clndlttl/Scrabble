from flask import url_for, current_app
import requests

letterValues = {
    'a':1, 'b':3,  'c':3, 'd':2, 'e':1,
    'f':4, 'g':2,  'h':4, 'i':1, 'j':8,
    'k':5, 'l':1,  'm':3, 'n':1, 'o':1,
    'p':3, 'q':10, 'r':1, 's':1, 't':1,
    'u':1, 'v':4,  'w':4, 'x':8, 'y':4, 'z':10
}

def sortAttempt(attempt, rv):
    # attempt = [ {'letter':'a','row':'2','col':'7'}, ... ]

    # check if all rows are the same (also sort lo to hi)
    rows = list(set([int(x['row']) for x in attempt]))
    cols = list(set([int(x['col']) for x in attempt]))
    rows.sort()
    cols.sort()

    current_app.logger.debug('rows = %s', rows)
    current_app.logger.debug('cols = %s', cols)

    # ensure word is continuous
    if len(rows) != 1 and len(cols) != 1:
        rv['ERROR'].append('Word is not continuous.')

    tuples = [(int(x['row']),int(x['col']),x['letter']) for x in attempt]
    tuples.sort()
    return tuples

def getFlatIndex(row, col):
    return 15*row + col

def isWordValid(word):
    url = "https://scrabblewordfinder.org/dictionary/" + word.lower()
    r = requests.get(url)
    lines = r.text.splitlines()
    idx = 0
    for line in lines:
        if 'check_dict_page' in line:
            result = lines[idx+3]
            if 'Yes' in result:
                return True
            else:
                return False
        else:
            idx += 1

def isLetter(char):
    return char not in ['.','#','@','%','$','*']

def scoreWords(words, rv):
    '''
    words = {
        324: [('d',None),('o','.'),('g','#')], // this means 'd' was already played, and 'g' is double letter value
        135: [ ]
    }
    '''
    current_app.logger.debug('words = %s',words)
    score = 0

    seenHashes = set()

    for hash in words:

        if hash in seenHashes:
            current_app.logger.debug('Redundant word found!')
            continue
        else:
            seenHashes.add(hash)

        w = ''
        wordBonus = 1

        for tup in words[hash]:

            letter = tup[0]
            space = tup[1]

            w += letter

            if space is None or space == '.':
                score += letterValues[letter]
            elif space == '#':
                score += letterValues[letter] * 2
            elif space == '@':
                score += letterValues[letter] * 3
            elif space == '%':
                score += letterValues[letter]
                wordBonus *= 2
            elif space == '$':
                score += letterValues[letter]
                wordBonus *= 3

        if not isWordValid(w):
            score = 0
            rv['ERROR'].append(f'{w} is not a valid word.')
            break

    return score * wordBonus


class TileFetcher:
    def __init__(self):
        self.codes = {'a': url_for('static', filename='tiles/a.jpg'),
                      'b': url_for('static', filename='tiles/b.jpg'),
                      'c': url_for('static', filename='tiles/c.jpg'),
                      'd': url_for('static', filename='tiles/d.jpg'),
                      'e': url_for('static', filename='tiles/e.jpg'),
                      'f': url_for('static', filename='tiles/f.jpg'),
                      'g': url_for('static', filename='tiles/g.jpg'),
                      'h': url_for('static', filename='tiles/h.jpg'),
                      'i': url_for('static', filename='tiles/i.jpg'),
                      'j': url_for('static', filename='tiles/j.jpg'),
                      'k': url_for('static', filename='tiles/k.jpg'),
                      'l': url_for('static', filename='tiles/l.jpg'),
                      'm': url_for('static', filename='tiles/m.jpg'),
                      'n': url_for('static', filename='tiles/n.jpg'),
                      'o': url_for('static', filename='tiles/o.jpg'),
                      'p': url_for('static', filename='tiles/p.jpg'),
                      'q': url_for('static', filename='tiles/q.jpg'),
                      'r': url_for('static', filename='tiles/r.jpg'),
                      's': url_for('static', filename='tiles/s.jpg'),
                      't': url_for('static', filename='tiles/t.jpg'),
                      'u': url_for('static', filename='tiles/u.jpg'),
                      'v': url_for('static', filename='tiles/v.jpg'),
                      'w': url_for('static', filename='tiles/w.jpg'),
                      'x': url_for('static', filename='tiles/x.jpg'),
                      'y': url_for('static', filename='tiles/y.jpg'),
                      'z': url_for('static', filename='tiles/z.jpg'),
                      '*': url_for('static', filename='tiles/free.jpg'),
                      '.': url_for('static', filename='tiles/em.jpg'),
                      '#': url_for('static', filename='tiles/dl.jpg'),
                      '%': url_for('static', filename='tiles/dw.jpg'),
                      '@': url_for('static', filename='tiles/tl.jpg'),
                      '$': url_for('static', filename='tiles/tw.jpg')
                      }

    def getURL(self, code):
        if code.lower() not in self.codes:
            return self.codes['.']
        return self.codes[code.lower()]
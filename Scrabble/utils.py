from flask import url_for
import requests

letterValues = {
    'a':1, 'b':3,  'c':3, 'd':2, 'e':1,
    'f':4, 'g':2,  'h':4, 'i':1, 'j':8,
    'k':5, 'l':1,  'm':3, 'n':1, 'o':1,
    'p':3, 'q':10, 'r':1, 's':1, 't':1,
    'u':1, 'v':4,  'w':4, 'x':8, 'y':4, 'z':10
}

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

def scoreTransverse(tr):
    word = tr[0]
    missing = tr[1]
    score = 0
    wordBonus = 1
    repaired = ''

    for ch in word:
        if isLetter(ch):
            score += letterValues[ch]
            repaired += ch
            continue

        if ch == '.':
            score += letterValues[missing]
        elif ch == '#':
            score += letterValues[missing] * 2
        elif ch == '@':
            score += letterValues[missing] * 3
        elif ch == '%':
            score += letterValues[missing]
            wordBonus *= 2
        elif ch == '$':
            score += letterValues[missing]
            wordBonus *= 3
        
        repaired += missing
    
    if not isWordValid(repaired):
        score = 0

    return (score * wordBonus, repaired)


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
                      '*': url_for('static', filename='tiles/cog.jpg'),
                      '.': url_for('static', filename='tiles/em.jpg'),
                      '#': url_for('static', filename='tiles/dl.jpg'),
                      '%': url_for('static', filename='tiles/dw.jpg'),
                      '@': url_for('static', filename='tiles/tl.jpg'),
                      '$': url_for('static', filename='tiles/tw.jpg')
                      }

    def get(self, code):
        if code.lower() not in self.codes:
            return self.codes['.']
        return self.codes[code.lower()]
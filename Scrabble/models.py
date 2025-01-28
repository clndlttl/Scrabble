from Scrabble import db, login
from datetime import datetime, timezone
import pytz
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from flask_login import UserMixin
from random import randint, shuffle
from sqlalchemy.ext.mutable import Mutable

def get_utcnow():
    return datetime.now(timezone.utc)

class MutableDict(Mutable, dict):
    @classmethod
    def coerce(cls, key, value):
        "Convert plain dictionaries to MutableDict."

        if not isinstance(value, MutableDict):
            if isinstance(value, dict):
                return MutableDict(value)

            # this call will raise ValueError
            return Mutable.coerce(key, value)
        else:
            return value

    def __setitem__(self, key, value):
        "Detect dictionary set events and emit change events."

        dict.__setitem__(self, key, value)
        self.changed()

    def __delitem__(self, key):
        "Detect dictionary del events and emit change events."

        dict.__delitem__(self, key)
        self.changed()

    def __getstate__(self):
        return dict(self)

    def __setstate__(self, state):
        self.update(state)


class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(64), unique=True)
    password_hash = db.Column(db.String(128))

    invites = db.relationship('Invite', backref='user', lazy='dynamic')

    def __repr__(self):
        return '<User {}>'.format(self.username)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

@login.user_loader
def load_user(id):
    return User.query.get(int(id))

class Invite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'))
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'))
    accepted = db.Column(db.Boolean, default=False)

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    timestamp = db.Column(db.DateTime, index=True, default=get_utcnow)
    isComplete = db.Column(db.Boolean, default=False)
    player1 = db.Column(db.Integer)
    player2 = db.Column(db.Integer)
    score1 = db.Column(db.Integer, default=0)
    score2 = db.Column(db.Integer, default=0)
    bank1 = db.Column(db.String(7), default='')
    bank2 = db.Column(db.String(7), default='')
    pool = db.Column(db.String(100))
    turn = db.Column(db.Integer, default=0)
    whosUp = db.Column(db.Integer)
    winner = db.Column(db.Integer)
    msg = db.Column(db.String(128), default='')
    invites = db.relationship('Invite', backref='game', lazy='dynamic')
    board = db.relationship('Board', backref='game', lazy='dynamic')

    def advanceTurn(self):
        self.turn += 1
        if self.turn % 2:
            self.whosUp = self.player2
        else:
            self.whosUp = self.player1

    def checkForWinner(self):
        if len(self.pool) == 0:
            if len(self.bank1) == 0 or len(self.bank2) == 0:
                self.isComplete = True
                if self.score1 > self.score2:
                    self.winner = self.player1
                elif self.score2 > self.score1:
                    self.winner = self.player2
                else:
                    self.winner = -1 # indicates a tie!

    def getPlayerStuff(self, user_id):
        if user_id == self.player1:
            return (1, self.bank1, self.score1) 
        elif user_id == self.player2:
            return (2, self.bank2, self.score2) 
    
    def setPlayerStuff(self, user_id, bank, newScore):
        if user_id == self.player1:
            self.bank1 = bank
            self.score1 = newScore
            self.refillBank(1)
        elif user_id == self.player2:
            self.bank2 = bank
            self.score2 = newScore 
            self.refillBank(2)

    def initPool(self):
        self.pool = 'aaaaaaaaabbccddddeeeeeeeeeeeeffggghhiiiiiiiiijjkkllllmmnnnnnnooooooooppqrrrrrrssssttttttuuuuvvwwxyyz'
    
    def refillBank(self, idx):
        if idx == 1:
            bank = self.bank1
        else:
            bank = self.bank2
        needed = 7 - len(bank)
        pool = list(self.pool)
        for i in range(needed):
            N = len(pool)
            if N > 0:
                ridx = randint(0,N-1)
                if idx == 1:
                    self.bank1 += pool[ridx]
                else:
                    self.bank2 += pool[ridx]
                del pool[ridx]
        self.pool = ''.join(pool)
    
    def setBank(self, idx, b):
        if idx == 1:
            self.bank1 = b
        elif idx == 2:
            self.bank2 = b

    def returnToPool(self, s):
        self.pool += s

    def numTilesPlayed(self):
        return 100 - len(self.pool) - len(self.bank1) - len(self.bank2)

    def printElapsedTime(self):
        elapsed = get_utcnow() - pytz.utc.localize(self.timestamp)
        s = ''
        nyears = int(elapsed.days / 365)
        if nyears:
            s += '{} year'.format(nyears)
            if nyears > 1:
                s += 's'
            s += ' ago'
            return s
        ndays = int(elapsed.days) % 365
        if ndays:
            s += '{} day'.format(ndays)
            if ndays > 1:
                s += 's'
            s += ' ago'
            return s
        nhours = int(elapsed.seconds / 3600)
        if nhours:
            s += '{} hour'.format(nhours)
            if nhours > 1:
                s += 's'
            s += ' ago'
            return s
        nmins = int((elapsed.seconds % 3600) / 60)
        if nmins:
            s += '{} min'.format(nmins)
            if nmins > 1:
                s += 's'
            s += ' ago'
            return s

        return 'a moment ago'


BLANK_BOARD = {'rows':[
['$','.','.','#','.','.','.','$','.','.','.','#','.','.','$'],
['.','%','.','.','.','@','.','.','.','@','.','.','.','%','.'],
['.','.','%','.','.','.','#','.','#','.','.','.','%','.','.'],
['#','.','.','%','.','.','.','#','.','.','.','%','.','.','#'],
['.','.','.','.','%','.','.','.','.','.','%','.','.','.','.'],
['.','@','.','.','.','@','.','.','.','@','.','.','.','@','.'],
['.','.','#','.','.','.','#','.','#','.','.','.','#','.','.'],
['$','.','.','#','.','.','.','*','.','.','.','#','.','.','$'],
['.','.','#','.','.','.','#','.','#','.','.','.','#','.','.'],
['.','@','.','.','.','@','.','.','.','@','.','.','.','@','.'],
['.','.','.','.','%','.','.','.','.','.','%','.','.','.','.'],
['#','.','.','%','.','.','.','#','.','.','.','%','.','.','#'],
['.','.','%','.','.','.','#','.','#','.','.','.','%','.','.'],
['.','%','.','.','.','@','.','.','.','@','.','.','.','%','.'],
['$','.','.','#','.','.','.','$','.','.','.','#','.','.','$'] 
]}

class Board(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'))
    data = db.Column(MutableDict.as_mutable(db.PickleType), nullable=True, default=BLANK_BOARD)
    chats = db.relationship('Chat', backref='board', lazy='dynamic')
    
    def setTile(self, row, col, char):
        tmp = self.data['rows']
        tmp[row][col] = char
        self.data['rows'] = tmp

    def getTile(self, row, col):
        tmp = self.data['rows']
        return tmp[row][col]

    def isAdjacent(self, row, col):
        tmp = self.data['rows']
        nonletters = ['.','#','@','%','$','*']
        # left
        if col > 0 and tmp[row][col-1] not in nonletters:
            return True
        # right
        if col < 14 and tmp[row][col+1] not in nonletters:
            return True
        # up
        if row > 0 and tmp[row-1][col] not in nonletters:
            return True
        # down
        if row < 14 and tmp[row+1][col] not in nonletters:
            return True
        return False

    def randomize(self):
        tmp = self.data['rows']
        allspaces = []
        for r in range(len(tmp)):
            allspaces += tmp[r] 
        shuffle(allspaces)
        for r in range(len(tmp)):
            for c in range(15):
                tmp[r][c] = allspaces[c + 15*r]
        self.data['rows'] = tmp

    def printBoard(self):
        rv = ''
        for row in self.data['rows']:
            rv += ''.join(row)
            rv += '\n'
        return rv



class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    board_id = db.Column(db.Integer, db.ForeignKey('board.id'))
    timestamp = db.Column(db.DateTime, index=True, default=get_utcnow)
    user = db.Column(db.String(8))
    text = db.Column(db.String(128))

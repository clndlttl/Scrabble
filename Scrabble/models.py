from flask import current_app
from Scrabble import db, app, login
from datetime import datetime
from werkzeug.security import generate_password_hash
from werkzeug.security import check_password_hash
from flask_login import UserMixin
from random import randint, shuffle

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), index=True, unique=True)
    email = db.Column(db.String(64), index=True, unique=True)
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

class OpenInvite(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'))
    spots = db.Column(db.Integer, default=0)

class Game(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(64))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    hasBegun = db.Column(db.Boolean, default=False)
    isComplete = db.Column(db.Boolean, default=False)
    player1 = db.Column(db.Integer)
    player2 = db.Column(db.Integer)
    player3 = db.Column(db.Integer)
    player4 = db.Column(db.Integer)
    score1 = db.Column(db.Integer, default=0)
    score2 = db.Column(db.Integer, default=0)
    score3 = db.Column(db.Integer, default=0)
    score4 = db.Column(db.Integer, default=0)
    bank1 = db.Column(db.String(7), default='')
    bank2 = db.Column(db.String(7), default='')
    bank3 = db.Column(db.String(7), default='')
    bank4 = db.Column(db.String(7), default='')
    pool = db.Column(db.String(100))
    turn = db.Column(db.Integer, default=0)
    whosUp = db.Column(db.Integer)
    winner = db.Column(db.Integer)
    invites = db.relationship('Invite', backref='game', lazy='dynamic')
    open_invites = db.relationship('OpenInvite', backref='game', lazy='dynamic')
    board = db.relationship('Board', backref='game', lazy='dynamic')

    def advanceTurn(self, idx):
        self.hasBegun = True
        self.turn += 1
        next_idx = idx+1
        if next_idx == 5:
            self.whosUp = self.player1
        elif next_idx == 4:
            if self.player4:
                self.whosUp = self.player4
            else:
                self.whosUp = self.player1
        elif next_idx == 3:
            if self.player3:
                self.whosUp = self.player3
            else:
                self.whosUp = self.player1
        elif next_idx == 2:
            self.whosUp = self.player2
    
    def checkForWinner(self):
        idx, bank, score = self.getPlayerStuff(self.whosUp)
        if len(bank) == 0 and len(self.pool) == 0:
            self.isComplete = True
            rank = {self.player1 : self.score1,
                    self.player2 : self.score2}
            if self.player3:
                rank[self.player3] = self.score3
            if self.player4:
                rank[self.player4] = self.score4
            self.winner = max(rank, key=rank.get)

    def getPlayerStuff(self, user_id):
        if user_id == self.player1:
            return (1, self.bank1, self.score1) 
        elif user_id == self.player2:
            return (2, self.bank2, self.score2) 
        elif user_id == self.player3:
            return (3, self.bank3, self.score3) 
        elif user_id == self.player4:
            return (4, self.bank4, self.score4)
        else:
            return (-1, '', 0)
    
    def setPlayerStuff(self, user_id, bank, newScore):
        if user_id == self.player1:
            self.bank1 = bank
            self.score1 = newScore
            self.refillBank(1)
        elif user_id == self.player2:
            self.bank2 = bank
            self.score2 = newScore 
            self.refillBank(2)
        elif user_id == self.player3:
            self.bank3 = bank
            self.score3 = newScore 
            self.refillBank(3)
        elif user_id == self.player4:
            self.bank4 = bank
            self.score4 = newScore 
            self.refillBank(4)

    def initPool(self):
        self.pool = 'aaaaaaaaabbccddddeeeeeeeeeeeeffggghhiiiiiiiiijjkkllllmmnnnnnnooooooooppqrrrrrrssssttttttuuuuvvwwxyyz'
    
    def refillBank(self, idx):
        needed = 7 - len(eval('self.bank'+str(idx)))
        pool = list(self.pool)
        for i in range(needed):
            N = len(pool)
            if N > 0:
                ridx = randint(0,N-1)
                exec('self.bank'+str(idx)+' += pool[ridx]')
                del pool[ridx]
        self.pool = ''.join(pool)
    
    def setBank(self, idx, b):
        exec('self.bank'+str(idx)+' = b')

    def returnToPool(self, s):
        self.pool += s

    def numTilesPlayed(self):
        return 100 - len(self.pool) - len(self.bank1) - len(self.bank2) - len(self.bank3) - len(self.bank4)

    def printElapsedTime(self):
        elapsed = datetime.utcnow() - self.timestamp
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

class Board(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    game_id = db.Column(db.Integer, db.ForeignKey('game.id'))
    row1  = db.Column(db.String(15), default='$..#...$...#..$')
    row2  = db.Column(db.String(15), default='.%...@...@...%.')
    row3  = db.Column(db.String(15), default='..%...#.#...%..')
    row4  = db.Column(db.String(15), default='#..%...#...%..#')
    row5  = db.Column(db.String(15), default='....%.....%....')
    row6  = db.Column(db.String(15), default='.@...@...@...@.')
    row7  = db.Column(db.String(15), default='..#...#.#...#..')
    row8  = db.Column(db.String(15), default='$..#...*...#..$')
    row9  = db.Column(db.String(15), default='..#...#.#...#..')
    row10 = db.Column(db.String(15), default='.@...@...@...@.')
    row11 = db.Column(db.String(15), default='....%.....%....')
    row12 = db.Column(db.String(15), default='#..%...#...%..#')
    row13 = db.Column(db.String(15), default='..%...#.#...%..')
    row14 = db.Column(db.String(15), default='.%...@...@...%.')
    row15 = db.Column(db.String(15), default='$..#...$...#..$')
    chats = db.relationship('Chat', backref='board', lazy='dynamic')
    
    def setTile(self, row, col, char):
        rowObj = eval('self.row'+str(row))
        rowlist = list(rowObj)
        rowlist[col-1] = char
        exec('self.row'+str(row)+' = \'\'.join(rowlist)')

    def getTile(self, row, col):
        rowObj = eval('self.row'+str(row))
        return rowObj[col-1]

    def randomize(self):
        allspaces = ''
        allspaces += self.row1
        allspaces += self.row2
        allspaces += self.row3
        allspaces += self.row4
        allspaces += self.row5
        allspaces += self.row6
        allspaces += self.row7
        allspaces += self.row8
        allspaces += self.row9
        allspaces += self.row10
        allspaces += self.row11
        allspaces += self.row12
        allspaces += self.row13
        allspaces += self.row14
        allspaces += self.row15
        biglist = list(allspaces)
        shuffle(biglist)
        self.row1 = ''.join(biglist[0:15])
        self.row2 = ''.join(biglist[15:30])
        self.row3 = ''.join(biglist[30:45])
        self.row4 = ''.join(biglist[45:60])
        self.row5 = ''.join(biglist[60:75])
        self.row6 = ''.join(biglist[75:90])
        self.row7 = ''.join(biglist[90:105])
        self.row8 = ''.join(biglist[105:120])
        self.row9 = ''.join(biglist[120:135])
        self.row10 = ''.join(biglist[135:150])
        self.row11 = ''.join(biglist[150:165])
        self.row12 = ''.join(biglist[165:180])
        self.row13 = ''.join(biglist[180:195])
        self.row14 = ''.join(biglist[195:210])
        self.row15 = ''.join(biglist[210:225])


class Chat(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    board_id = db.Column(db.Integer, db.ForeignKey('board.id'))
    timestamp = db.Column(db.DateTime, index=True, default=datetime.utcnow)
    user = db.Column(db.String(8))
    text = db.Column(db.String(128))

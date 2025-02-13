import os
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
import json
from time import sleep
from flask import url_for, current_app
from Scrabble import db
from Scrabble.models import User, Board

letterValues = {
    'a':1, 'b':3,  'c':3, 'd':2, 'e':1,
    'f':4, 'g':2,  'h':4, 'i':1, 'j':8,
    'k':5, 'l':1,  'm':3, 'n':1, 'o':1,
    'p':3, 'q':10, 'r':1, 's':1, 't':1,
    'u':1, 'v':4,  'w':4, 'x':8, 'y':4, 'z':10
}

def getUsername(id):
    user = User.query.filter_by(id=id).first()
    if user is None:
        return "NotFound"
    return user.username


def sortAttempt(attempt, rv):
    # attempt = [ {'letter':'a','row':'2','col':'7'}, ... ]

    # check if all rows are the same (also sort lo to hi)
    rows = list(set([int(x['row']) for x in attempt]))
    cols = list(set([int(x['col']) for x in attempt]))
    rows.sort()
    cols.sort()

    # ensure word is continuous
    if len(rows) != 1 and len(cols) != 1:
        rv['ERROR'].append('Word is not continuous.')

    tuples = [(int(x['row']),int(x['col']),x['letter']) for x in attempt]
    tuples.sort()
    return tuples

def getFlatIndex(row, col):
    return 15*row + col

def isWordValid(word):
    qry = {'query': word}
    current_app.redis.xadd('TrieChannel', qry)
    current_app.logger.debug("Validating word: %s", word)

    # Wait for the key to appear in the redis key store
    while not current_app.redis.exists(word):
        current_app.logger.debug('...waiting...')
        sleep(0.5)
    
    qrStr = current_app.redis.get(word)
    if qrStr == 'True':
        return True
    else:
        return False

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
    finalScore = 0

    seenHashes = set()

    wordScoreTuples = []

    for hash in words:

        if hash in seenHashes:
            current_app.logger.debug('Redundant word found!')
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

        if not isWordValid(w):
            finalScore = 0
            rv['ERROR'].append(f'"{w}" is not a valid word.')
            wordScoreTuples.clear()
            break
        else:
            finalScore += thisScore * wordBonus
            wordScoreTuples.append( (w, thisScore * wordBonus) )

    return finalScore, wordScoreTuples


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


def util_playWord(user_id, board_id, attempt) -> str:

    rv = {'ERROR':[]}

    board = Board.query.filter_by(id=board_id).first()
    if board is None:
        rv['ERROR'].append('ERROR: Cannot find board')

    if len(attempt) == 0:
        rv['ERROR'].append('Drag at least one letter to the board.')

    if board.game.winner is not None:
        rv['ERROR'].append('Game is over.')

    attemptList = sortAttempt(attempt, rv)
    
    # Done with basic validation
    if len(rv['ERROR']) > 0:
        current_app.logger.debug('%s',rv['ERROR'])
        return json.dumps(rv)

    # build a set of attempt locations
    attemptIndices = { getFlatIndex(tup[0],tup[1]) : tup[2] for tup in attemptList }
    
    isStar = False
    isAdjacent = False

    _, bank, playerScore = board.game.getPlayerStuff(user_id)

    words = {}

    for letter in attemptList:

        # letter is a tuple of (rowIdx, colIdx, letter)
        row = letter[0]
        col = letter[1]

        # check for board adjacency first
        isAdjacent |= board.isAdjacent(row, col)
 
        # what space does this letter cover?
        space = board.getTile(row, col)
        if space == '*':
            isStar = True

        # look for a horizontal word
        w = []
        hash = 0
        # rewind to start of word
        colStart = col
        while colStart > 0 and (isLetter( board.getTile(row, colStart-1) ) or getFlatIndex(row, colStart-1) in attemptIndices):
            colStart -= 1
        # add first letter, noting if it's already there or new
        fi = getFlatIndex(row,colStart)
        hash += fi
        if fi in attemptIndices:
            w.append( (attemptIndices[fi], board.getTile(row, colStart)) )
        else:
            w.append( (board.getTile(row, colStart), None) )
        # read out the word
        colEnd = colStart
        while colEnd < 14 and (isLetter( board.getTile(row, colEnd+1) ) or (getFlatIndex(row,colEnd+1) in attemptIndices)):
            colEnd += 1
            fi = getFlatIndex(row,colEnd)
            hash += fi
            if getFlatIndex(row,colEnd) in attemptIndices:
                w.append( (attemptIndices[fi], board.getTile(row, colEnd)) )
            elif isLetter( board.getTile(row,colEnd) ):
                w.append( (board.getTile(row, colEnd), None) )
            else:
                rv['ERROR'].append('Word is not continuous.')
        if colEnd != colStart:
            words[hash] = w

        # look for a vertical word
        w = []
        hash = 0
        # rewind to start of word
        rowStart = row
        while rowStart > 0 and (isLetter( board.getTile(rowStart-1, col) ) or getFlatIndex(rowStart-1, col) in attemptIndices):
            rowStart -= 1
        # add first letter
        fi = getFlatIndex(rowStart,col)
        hash += fi
        if getFlatIndex(rowStart,col) in attemptIndices:
            w.append( (attemptIndices[fi], board.getTile(rowStart, col)) )
        else:
            w.append( (board.getTile(rowStart, col), None) )
        # read out the word
        rowEnd = rowStart
        while rowEnd < 14 and (isLetter( board.getTile(rowEnd+1, col)) or (getFlatIndex(rowEnd+1,col) in attemptIndices)):
            rowEnd += 1
            fi = getFlatIndex(rowEnd,col)
            hash += fi
            if getFlatIndex(rowEnd,col) in attemptIndices:
                w.append( (attemptIndices[fi], board.getTile(rowEnd, col)) )
            elif isLetter( board.getTile(rowEnd, col) ):
                w.append( (board.getTile(rowEnd, col), None) )
            else:
                rv['ERROR'].append('Word is not continuous.')
        if rowEnd != rowStart:
            words[hash] = w

    # word must touch at least one played tile, unless it's the first move
    if board.game.numTilesPlayed() > 0 and not isAdjacent:
        rv['ERROR'].append('Word must touch at least one other tile')
    # first play must cover the star
    elif board.game.numTilesPlayed() == 0 and not isStar:
        rv['ERROR'].append('First play must cover the logo tile')
    
    if len(rv['ERROR']) > 0:
        current_app.logger.debug('%s',rv['ERROR'])
        return json.dumps(rv)

    # Validate and score all words
    score = 0
    thisScore, wordScoreTuples = scoreWords(words, rv)
    if thisScore == 0:
        return json.dumps(rv)
    score += thisScore

    newmsg = []
    
    # Check for bingo (50 points for using all 7 letters)
    if len(attemptList) == 7:
        score += 50
        newmsg.append(' all 7 tiles for 50 bonus points')

    # Write in the new tiles
    for tup in attemptList:
        board.setTile( tup[0], tup[1], tup[2] )
    
    # remove used letters from player's bank
    bankCopy = list(bank)
    for tup in attemptList:
        bankCopy.remove(tup[2])

    # update/refill bank, incr score
    board.game.setPlayerStuff(user_id, ''.join(bankCopy), playerScore + score)

    # advance turn
    board.game.advanceTurn()

    # check for game end
    board.game.checkForWinner()

    for tup in wordScoreTuples:    
        newmsg.append(f' "{tup[0]}" for {tup[1]} points')
    
    if board.game.winner is not None:
        newmsg.append(f' {getUsername(board.game.winner)} is the winner!!!')
    
    board.game.msg = f'{getUsername(user_id)} played ' + ','.join(newmsg)
    
    db.session.commit()

    # User 1 must be username AI
    if board.game.whosUp == 1:
        launch_AI_task(board_id)
    else:
        sendEmail(board.game.whosUp, board.game.msg)

    return json.dumps(rv)


def launch_AI_task(board_id):
    #taskName = f'socket_{port}'
    #found = Task.query.filter_by(name=taskName).first()
    #if found:
    #    if not found.complete:
    #        return
    #    Task.query.filter_by(name=taskName).delete()
    #    db.session.commit()
    
    args = [board_id]
    #rq_job = current_app.task_queue.enqueue('Scrabble.task.makeChatGPTmove', *args, job_timeout=120)
    _ = current_app.task_queue.enqueue('Scrabble.task.trieSearch', *args, job_timeout=120)
    
    #task = Task(id=rq_job.get_id(), name=taskName, timeout_sec=-1)
    #db.session.add(task)
    #db.session.commit()

def sendEmail(userId, moveInfoString):
    # using SendGrid's Python Library
    user = User.query.filter_by(id=userId).first()
    if user is None:
        return

    load_dotenv(dotenv_path='/var/www/.env')
    current_app.logger.debug('sending email to %s', user.email)
    
    message = Mail(
        from_email='colin@inertialframe.dev',
        to_emails=user.email,
        subject="It's your move in Scrabble!",
        html_content=f'''
{moveInfoString}!<br><br>
Login at https://www.colinfox.dev to make your move.
        '''
    )

    try:
        sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
        response = sg.send(message)
        #current_app.logger.debug(response.status_code)
        #current_app.logger.debug(response.body)
        #current_app.logger.debug(response.headers)
    except Exception as e:
        current_app.logger.debug(str(e))

def sendInviteEmail(userName, fromUserName):
    # using SendGrid's Python Library
    user = User.query.filter_by(username=userName).first()
    if user is None:
        return

    load_dotenv(dotenv_path='/var/www/.env')
    current_app.logger.debug('sending invite email to %s', user.email)
    
    message = Mail(
        from_email='colin@inertialframe.dev',
        to_emails=user.email,
        subject=f"{fromUserName} has challenged you to a game of Scrabble!",
        html_content='Login at https://www.colinfox.dev to accept or decline the invitation.'
    )

    try:
        sg = SendGridAPIClient(os.getenv('SENDGRID_API_KEY'))
        response = sg.send(message)
        #current_app.logger.debug(response.status_code)
        #current_app.logger.debug(response.body)
        #current_app.logger.debug(response.headers)
    except Exception as e:
        current_app.logger.debug(str(e))
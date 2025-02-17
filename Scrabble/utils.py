import os
import json
from time import sleep
from dotenv import load_dotenv
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail
from flask import url_for, current_app
from Scrabble import db
from Scrabble.models import User, Board
from gameUtils import *


def getUsername(id):
    user = User.query.filter_by(id=id).first()
    if user is None:
        return "NotFound"
    return user.username


def sortAttempt(attempt: list[dict[str,str]], errorList: list[str]) -> list[tuple[int,int,str]]:
    # attempt = [ {'letter':'a','row':'2','col':'7'}, ... ]

    # check if all rows are the same (also sort lo to hi)
    rows = list(set([int(x['row']) for x in attempt]))
    cols = list(set([int(x['col']) for x in attempt]))
    rows.sort()
    cols.sort()

    # ensure word is continuous
    if len(rows) != 1 and len(cols) != 1:
        errorList.append('Word is not continuous.')

    tuples = [(int(x['row']),int(x['col']),x['letter']) for x in attempt]
    tuples.sort()
    return tuples


def isWordValid(word):

    if current_app.redis.exists(word):
        return True

    qry = {'query': word}
    current_app.redis.xadd('TrieChannel', qry)

    # Wait for the key to appear in the redis key store
    sleep(1)
    return current_app.redis.exists(word)


def scoreWords(words, errorList: list[str]):
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
            errorList.append(f'"{w}" is not a valid word.')
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


def util_playWord(user_id: int, board_id: int, attempt: list[dict[str,str]], prevMsg: str = '', iamabot: bool = False) -> str:

    errorList = []

    board = Board.query.filter_by(id=board_id).first()
    if board is None:
        errorList.append('ERROR: Cannot find board')

    if len(attempt) == 0:
        errorList.append('Drag at least one letter to the board.')

    if board.game.winner is not None:
        errorList.append('Game is over.')

    current_app.logger.debug('attempt: %s', attempt)

    # Order and ensure continuity
    attemptList = sortAttempt(attempt, errorList)
    
    current_app.logger.debug('attemptList: %s', attemptList)
    
    # Done with basic validation
    if len(errorList) > 0:
        current_app.logger.debug('%s',errorList)
        return json.dumps({'ERROR':errorList})

    _, bank, playerScore = board.game.getPlayerStuff(user_id)

    mat = board.getRows()

    ########
    words, isStar, isAdj = findWords(mat, attemptList, errorList)
    ########

    # word must touch at least one played tile, unless it's the first move
    if board.game.numTilesPlayed() > 0 and not isAdj:
        errorList.append('Word must touch at least one other tile')
    # first play must cover the star
    elif board.game.numTilesPlayed() == 0 and not isStar:
        errorList.append('First play must cover the logo tile')
    
    if len(errorList) > 0:
        current_app.logger.debug('%s',errorList)
        return json.dumps({'ERROR':errorList})

    # Validate and score all words
    score = 0
    thisScore, wordScoreTuples = scoreWords(words, errorList)
    if thisScore == 0:
        return json.dumps({'ERROR':errorList})
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
    
    currMsg = f'{getUsername(user_id)} played ' + ','.join(newmsg) + '. '
    
    board.game.msg = f'{prevMsg}{currMsg}'

    db.session.commit()

    # User 1 is the bot
    if board.game.whosUp == 1 and len(prevMsg) == 0:
        runBot(board_id, currMsg)
    elif user_id != 1:
        # Don't send an email after bot plays
        sendEmail(board.game.whosUp, board.game.msg)

    return json.dumps({'ERROR':errorList})


def util_swap(user_id: int, board_id: int, word: str, prevMsg: str = '', iamabot: bool = False) -> str:
    
    errorList = []

    board = Board.query.filter_by(id=board_id).first()
    if board is None:
        errorList.append('ERROR: Cannot find board.')

    if word == '':
        errorList.append('Drag 1 to 7 letters to the swap area, then press swap')

    if len(word) > len(board.game.pool):
        errorList.append(f'Swap failed: only {len(board.game.pool)} letters left in the pool!')

    # Done with basic validation
    if len(errorList) > 0:
        return json.dumps({'ERROR':errorList})

    removed = []
    idx, bank, _ = board.game.getPlayerStuff(user_id)
    bankList = list(bank)

    for letter in word.lower():
        bankList.remove(letter)
        removed.append(letter)

    board.game.setBank(idx, ''.join(bankList))
    board.game.refillBank(idx)
    board.game.returnToPool(''.join(removed))

    # advance turn
    board.game.advanceTurn()

    currMsg = f'{getUsername(user_id)} swapped {len(removed)} tiles. '

    board.game.msg = f'{prevMsg}{currMsg}'

    db.session.commit()
    
    # User 1 must be the Bot
    if board.game.whosUp == 1 and not iamabot:
        runBot(board_id, currMsg)
    elif user_id != 1:
        sendEmail(board.game.whosUp, board.game.msg)
    

    return json.dumps({'ERROR':errorList})


def runBot(board_id: int, prevMsg: str):
    board = Board.query.filter_by(id=board_id).first()
    if board is None:
        return
    
    boardStr = board.printBoard()

    _, bankStr, _ = board.game.getPlayerStuff(1)

    try:
        moveInfo = {'boardStr': boardStr, 'bankStr': bankStr}
        current_app.redis.xadd('TrieChannel', moveInfo)
    except Exception as e:
        current_app.logger.critical(str(e))
        return

    current_app.logger.debug("Sent moveInfo, waiting for moveResponse...")
    
    # Blocking call to listen for messages
    message = current_app.redis.xread({'TrieChannel': '$'}, None, 0)
    
    resp = message[0][1][0][1]
    
    # The message is a dictionary with a 'type' field
    if 'moveResponse' in resp:
        move = json.loads(resp['moveResponse'])
        current_app.logger.debug('move = %s', move)

        if move == 'null':
            # Bot couldn't find a move, just swap all tiles
            rvStr = util_swap(1, board_id, bankStr, prevMsg=prevMsg, iamabot=True)
        else:
            # move is a list of tuples like [ (row,col,letter), ... ]
            attempt = [{'letter':tup[2],'row':tup[0],'col':tup[1]} for tup in move]
            rvStr = util_playWord(1, board_id, attempt, prevMsg=prevMsg, iamabot=True)
        
        rv = json.loads(rvStr)
        
        if len(rv['ERROR']) > 0:
            current_app.logger.debug('trieSearch error: %s', rv['ERROR'])
        else:
            current_app.logger.debug('trieSearch move success!')


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
{moveInfoString}<br><br>
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

#from rq import get_current_job
from Scrabble import create_app
#from Scrabble.prompt import AIPlayer, buildNudge
from Scrabble.utils import util_playWord
from Scrabble.models import Board
import json

app = create_app()
app.app_context().push()

def trieSearch(board_id):
    board = Board.query.filter_by(id=board_id).first()
    if board is None:
        return
    
    boardStr = board.printBoard()
    #app.logger.debug('Board: \n%s',boardStr)

    _, bankStr, _ = board.game.getPlayerStuff(1)
    #app.logger.debug('Bank: \n%s',bankStr)

    try:
        moveInfo = {'boardStr': boardStr, 'bankStr': bankStr}
        app.redis.xadd('TrieChannel', moveInfo)
    except Exception as e:
        app.logger.critical(str(e))
        return

    app.logger.debug("Sent moveInfo, waiting for moveResponse...")
    
    # Blocking call to listen for messages
    message = app.redis.xread({'TrieChannel': '$'}, None, 0)
    
    resp = message[0][1][0][1]
    
    # The message is a dictionary with a 'type' field
    if 'moveResponse' in resp:
        move = json.loads(resp['moveResponse'])
        app.logger.debug('move = %s', move)

        # move is a list of tuples like [ (row,col,letter), ... ]
        attempt = [{'letter':tup[2],'row':tup[0],'col':tup[1]} for tup in move]
        
        rvStr = util_playWord(1, board_id, attempt)
        
        rv = json.loads(rvStr)
        
        if len(rv['ERROR']) > 0:
            app.logger.debug('trieSearch error: %s', rv['ERROR'])
        else:
            app.logger.debug('trieSearch move success!')


def makeChatGPTmove(board_id):
    board = Board.query.filter_by(id=board_id).first()
    if board is None:
        return

    boardStr = board.printBoard()
    app.logger.debug('Board: \n%s',boardStr)

    _, bankStr, _ = board.game.getPlayerStuff(1)
    app.logger.debug('Bank: \n%s',bankStr)

    nudge = ''

    for iter in range(3):
        try:
            move = AIPlayer(boardStr, bankStr, nudge, app.logger)
        except Exception as e:
            app.logger.critical(str(e))
            return

        app.logger.debug('move #%i: %s', iter, move)

        # move is a list of tuples like [ (row,col,letter), ... ]
        attempt = [{'letter':tup[2],'row':tup[0],'col':tup[1]} for tup in move]

        rvStr = util_playWord(1, board_id, attempt)

        rv = json.loads(rvStr)

        if len(rv['ERROR']) > 0:
            app.logger.debug('AI error: %s', rv['ERROR'])
            nudge += buildNudge(move, rv['ERROR'])
        else:
            app.logger.debug('AI move success!')
            break

from flask import request, url_for, flash, redirect, render_template, current_app
from flask_login import current_user, login_user, logout_user, login_required
from Scrabble import db
from Scrabble.main import bp
from Scrabble.main.forms import LoginForm, SignupForm
from Scrabble.main.forms import CreateGameForm
from Scrabble.models import User, Invite, Game, Board, Chat
from Scrabble.utils import TileFetcher, isLetter, scoreWords, sortAttempt, getFlatIndex
import json
import hashlib
import os


def generate_cache_buster(file_path):
    with open(file_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


def getUsername(id):
    user = User.query.filter_by(id=id).first()
    if user is None:
        return "NotFound"
    return user.username


def strlen(s):
    return len(s)


@bp.before_app_request
def register_jinja_globals():
    current_app.jinja_env.globals['getUsername'] = getUsername
    current_app.jinja_env.globals['strlen'] = strlen


@bp.route("/")
@bp.route("/index")
def index():
    return redirect(url_for('main.home'))


@bp.route("/home")
@login_required
def home():
    css_file_path = os.path.join(current_app.config['CSS_DIR'], 'homepage.css')
    css_hash = generate_cache_buster(css_file_path)
    return render_template('homepage.html', css_hash=css_hash)


@bp.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=form.username.data).first()
        if user is None or not user.check_password(form.password.data):
            flash('Invalid username or password')
            return redirect(url_for('main.login'))
        login_user(user, remember=False)
        next_page = request.args.get('next')
        if not next_page:
            next_page = url_for('main.home')
        return redirect(next_page)
    css_file_path = os.path.join(current_app.config['CSS_DIR'], 'base.css')
    css_hash = generate_cache_buster(css_file_path)
    return render_template('login.html', form=form, css_hash=css_hash)


@bp.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('main.index'))


@bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    form = SignupForm()
    if form.validate_on_submit():
        user = User(username=form.username.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()
        
        flash('Sign Up successful!')
        return redirect(url_for('main.login'))
    css_file_path = os.path.join(current_app.config['CSS_DIR'], 'base.css')
    css_hash = generate_cache_buster(css_file_path)
    return render_template('signup.html', form=form, css_hash=css_hash)


@bp.route('/createGame', methods=['GET', 'POST'])
@login_required
def createGame():
    form = CreateGameForm()
    if form.validate_on_submit():

        user2 = User.query.filter_by(username=form.opponent.data).first()

        game = Game(name=form.name.data, player1=current_user.id, player2=user2.id, whosUp=current_user.id)
        game.initPool()
        db.session.add(game)

        found_game = Game.query.filter_by(name=form.name.data).first()
        found_game.refillBank(1)

        board = Board(game_id=game.id)
        db.session.add(board)
        db.session.commit()
        found_board = Board.query.filter_by(game_id=game.id).first()
        if form.random.data:
            found_board.randomize()

        player1 = current_user.id
        invite1 = Invite(user_id=player1, game_id=found_game.id, accepted=True)
        db.session.add(invite1)

        player2 = user2.id
        invite2 = Invite(user_id=player2, game_id=found_game.id, accepted=False)
        db.session.add(invite2)

        db.session.commit()

        return redirect(url_for('main.home'))

    css_file_path = os.path.join(current_app.config['CSS_DIR'], 'base.css')
    css_hash = generate_cache_buster(css_file_path)
    return render_template('createGame.html', form=form, css_hash=css_hash)


@bp.route('/showLobby')
@login_required
def showLobby():
    personal_invites = Invite.query.filter_by(user_id=current_user.id)

    accepted = []
    accepted_game_ids = []

    pending = []
    pending_game_ids = []

    for i in personal_invites:
        if i.accepted:
            accepted.append(i.game)
            accepted_game_ids.append(i.game.id)
        else:
            pending.append(i.game)
            pending_game_ids.append(i.game.id)
    
    tileFetcher = TileFetcher()

    return render_template('lobby.html', pending=pending, accepted=accepted, tiles=tileFetcher)


@bp.route('/joinGame', methods=['POST'])
@login_required
def joinGame():
    id = request.values.get('game_id')

    game = Game.query.filter_by(id=id).first()

    invite = Invite.query.filter_by(user_id=current_user.id).filter_by(game_id=id).first()
    if invite is not None:
        invite.accepted = True

    game.player2 = current_user.id
    game.refillBank(2)

    db.session.commit()
    return redirect(url_for('main.showLobby'))


@bp.route('/deleteGame', methods=['POST'])
@login_required
def deleteGame():
    id = request.values.get('game_id')

    board = Board.query.filter_by(game_id=id).first()
    Chat.query.filter_by(board_id=board.id).delete()

    Board.query.filter_by(game_id=id).delete()
    Invite.query.filter_by(game_id=id).delete()
    Game.query.filter_by(id=id).delete()

    db.session.commit()
    return redirect(url_for('main.showLobby'))


@bp.route('/showBoard')
@login_required
def showBoard():
    id = request.values.get('id')
    board = Board.query.filter_by(game_id=id).first()
    tileFetcher = TileFetcher()

    _, bankstr, _ = board.game.getPlayerStuff(current_user.id) 
    bank = list(bankstr) 

    return render_template('board.html', board=board, tiles=tileFetcher, bank=bank)


@bp.route('/playWord', methods=['POST'])
@login_required
def playWord():
    board_id = request.values.get('board_id')
    attempt = json.loads(request.values.get('attempt'))

    current_app.logger.debug('attempt = %s',attempt)

    rv = {'ERROR':[]}

    board = Board.query.filter_by(id=board_id).first()
    if board is None:
        rv['ERROR'].append('ERROR: Cannot find board')

    if len(attempt) == 0:
        rv['ERROR'].append('Drag at least one letter to the board.')

    attemptList = sortAttempt(attempt, rv)

    current_app.logger.debug('attemptList = %s',attemptList)

    # build a set of attempt locations
    #attemptIndices = set([ getFlatIndex(tup[0],tup[1]) for tup in attemptList ])
    attemptIndices = { getFlatIndex(tup[0],tup[1]) : tup[2] for tup in attemptList }

    # Done with basic validation
    if len(rv['ERROR']) > 0:
        return json.dumps(rv)

    isStar = False
    isAdjacent = False

    _, bank, playerScore = board.game.getPlayerStuff(current_user.id)

    words = {}

    for letter in attemptList:

        # letter is a tuple of (rowIdx, colIdx, letter)
        row = letter[0]
        col = letter[1]
        let = letter[2]

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
        return json.dumps(rv)
    # first play must cover the star
    elif board.game.numTilesPlayed() == 0 and not isStar:
        rv['ERROR'].append('First play must cover the logo tile')
        return json.dumps(rv)
    
    if len(rv['ERROR']) > 0:
        return json.dumps(rv)

    # Validate and score all words
    score = 0
    thisScore, scoredWordDict = scoreWords(words, rv)
    if thisScore == 0:
        return json.dumps(rv)
    else:
        score += thisScore

    # Check for bingo (50 points for using all 7 letters)
    if len(attemptList) == 7:
        score += 50

    # Write in the new tiles
    for tup in attemptList:
        board.setTile( tup[0], tup[1], tup[2] )
    
    # remove used letters from player's bank
    bankCopy = list(bank)
    for tup in attemptList:
        bankCopy.remove(tup[2])

    # update/refill bank, incr score
    board.game.setPlayerStuff(current_user.id, ''.join(bankCopy), playerScore + score)

    # advance turn
    board.game.advanceTurn()

    # check for game end
    board.game.checkForWinner()

    db.session.commit()

    for w in scoredWordDict:
        flash(f'You played "{w}" for {scoredWordDict[w]} points!')
    if board.game.winner is not None:
        flash(f'{getUsername(board.game.winner)} has won the game!')

    # return json to the client
    return json.dumps(rv)


@bp.route('/swapTiles', methods=['POST'])
@login_required
def swapTiles():
    board_id = request.values.get('board_id')
    swap = json.loads(request.values.get('swap'))
    current_app.logger.debug(swap)
    word = ''.join(swap)

    current_app.logger.debug('swap word = %s', word)

    rv = {'ERROR':[]}

    board = Board.query.filter_by(id=board_id).first()
    if board is None:
        rv['ERROR'].append('ERROR: Can\'t find board')

    if word == '':
        rv['ERROR'].append('Please enter one to seven letters to swap<br>')

    if len(word) > len(board.game.pool):
        rv['ERROR'].append('Swap failed, there are only {} letters in the pool'.format(len(board.game.pool)))

    # Done with basic validation
    if len(rv['ERROR']) > 0:
        return json.dumps(rv)

    removed = []
    idx, bank, _ = board.game.getPlayerStuff(current_user.id)
    bankList = list(bank)

    for letter in word.lower():
        if letter not in bankList:
            rv['ERROR'].append('You don\'t have letter {} to swap'.format(letter))
            return json.dumps(rv)
        bankList.remove(letter)
        removed.append(letter)

    board.game.setBank(idx, ''.join(bankList))
    board.game.refillBank(idx)
    board.game.returnToPool(''.join(removed))

    # advance turn
    board.game.advanceTurn()

    db.session.commit()

    flash('You swapped {} tiles'.format(len(word)))

    return json.dumps(rv)

@bp.route('/postChat', methods=['POST'])
@login_required
def postChat():
    user = request.values.get('user')
    text = request.values.get('text')
    board_id = request.values.get('board_id')

    chat = Chat(board_id=board_id, user=user, text=text)
    db.session.add(chat)
    db.session.commit()

    chats = Chat.query.filter_by(board_id=board_id)

    return render_template('chat_history.html', chats=chats)

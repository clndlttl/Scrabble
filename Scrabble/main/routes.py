from flask import request, url_for, flash, redirect, render_template, current_app
from flask_login import current_user, login_user, logout_user, login_required
from Scrabble import db
from Scrabble.main import bp
from Scrabble.main.forms import LoginForm, SignupForm
from Scrabble.main.forms import CreateGameForm
from Scrabble.models import User, Invite, Game, Board, Chat
from Scrabble.utils import TileFetcher, isWordValid, isLetter, scoreTransverse, letterValues
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
    word = request.values.get('word')
    direction = request.values.get('direction')
    rowstr = request.values.get('row')
    colstr = request.values.get('col')

    rv = {'ERROR':[]}
    
    board = Board.query.filter_by(id=board_id).first()
    if board is None:
        rv['ERROR'].append('ERROR: Can\'t find board')

    if rowstr == '-' and colstr == '-':
        rv['ERROR'].append('Please click the starting letter location<br>')

    if direction == 'undefined':
        rv['ERROR'].append('Please specify Across or Down<br>')

    if word == '':
        rv['ERROR'].append('Please enter a word<br>')
    elif not isWordValid(word):
        rv['ERROR'].append('{} is not a valid word'.format(word))

    # Done with basic validation
    if len(rv['ERROR']) > 0:
        return json.dumps(rv)

    isHorizontal = (direction == 'A')
    isVertical = not isHorizontal

    if isHorizontal:
        col_incr = 1
        row_incr = 0
    else:
        col_incr = 0
        row_incr = 1

    score = 0
    wordBonus = 1
    isStar = False
    isOverlap = False

    transverse = []
    toWrite = []

    playerIdx, bank, playerScore = board.game.getPlayerStuff(current_user.id)

    # make a copy of the bank
    bankCopy = list(bank)

    row = int(rowstr)
    col = int(colstr)

    for letter in word.lower():

        # range check
        if row < 1 or row > 15 or col < 1 or col > 15:
            rv['ERROR'].append('Word goes off board')
            return json.dumps(rv)

        letterBonus = 1

        tile = board.getTile(row, col)

        if not isLetter(tile):

            # find transverse words
            if isVertical:
                w = ''
                colStart = col
                while colStart > 1 and isLetter( board.getTile(row, colStart-1) ):
                    colStart -= 1
                w += board.getTile(row, colStart)
                colEnd = colStart
                while colEnd < 15 and (isLetter( board.getTile(row, colEnd+1) ) or ((colEnd+1) == col)):
                    colEnd += 1
                    w += board.getTile(row, colEnd)
                wlen = colEnd - colStart
                if wlen > 0:
                    transverse.append( (w, letter) )
            else:
                w = ''
                rowStart = row
                while rowStart > 1 and isLetter( board.getTile(rowStart-1, col) ):
                    rowStart -= 1
                w += board.getTile(rowStart, col)
                rowEnd = rowStart
                while rowEnd < 15 and (isLetter( board.getTile(rowEnd+1, col)) or ((rowEnd+1) == row)):
                    rowEnd += 1
                    w += board.getTile(rowEnd, col)
                wlen = rowEnd - rowStart
                if wlen > 0:
                    transverse.append( (w, letter) )

            if tile == '*':
                isStar = True
            elif tile == '#':
                letterBonus = 2
            elif tile == '@':
                letterBonus = 3
            elif tile == '%':
                wordBonus *= 2
            elif tile == '$':
                wordBonus *= 3

            if letter not in bankCopy:
                rv['ERROR'].append('You don\'t have letter {}'.format(letter))
                return json.dumps(rv)
            else:
                toWrite.append( (row, col, letter) )
                bankCopy.remove(letter)

        else:
            if tile != letter:
                rv['ERROR'].append('Tile mismatch detected')
                return json.dumps(rv)
            isOverlap = True

        score += letterValues[letter] * letterBonus

        row += row_incr
        col += col_incr

    score *= wordBonus

    # word must touch at least one played tile, unless it's the first move
    if board.game.numTilesPlayed() > 0 and len(transverse) == 0 and not isOverlap:
        rv['ERROR'].append('Word must touch at least one other tile')
        return json.dumps(rv)

    # first play must cover the star
    if board.game.numTilesPlayed() == 0 and not isStar:
        rv['ERROR'].append('First play must cover the center tile')
        return json.dumps(rv)

    # must use at least one letter from bank
    if len(toWrite) == 0:
        rv['ERROR'].append('You must place at least one tile')
        return json.dumps(rv)

    # Validate and score all transverse words
    for tr in transverse:
        transverseScore, repairedWord = scoreTransverse(tr)
        if transverseScore == 0:
            rv['ERROR'].append('{} is not a valid word'.format(repairedWord))
            return json.dumps(rv)
        else:
            score += transverseScore

    # Check for bingo (50 points for using all 7 letters)
    if len(toWrite) == 7:
        score += 50

    # Write in the new tiles
    for lc in toWrite:
        board.setTile( lc[0], lc[1], lc[2] )

    # update/refill bank, incr score
    board.game.setPlayerStuff(current_user.id, ''.join(bankCopy), playerScore + score)

    # advance turn
    board.game.advanceTurn()

    # check for game end
    board.game.checkForWinner()

    db.session.commit()

    flash('You played \'{}\' for {} points!'.format(word.lower(), score))
    if board.game.winner is not None:
        flash('{} has won the game!'.format(getUsername(board.game.winner)))

    # return json to the client
    return json.dumps(rv)

@bp.route('/swapTiles', methods=['POST'])
@login_required
def swapTiles():
    board_id = request.values.get('board_id')
    word = request.values.get('word')

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

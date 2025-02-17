from flask import request, url_for, flash, redirect, render_template, current_app
from flask_login import current_user, login_user, logout_user, login_required
from Scrabble import db
from Scrabble.main import bp
from Scrabble.main.forms import LoginForm, SignupForm
from Scrabble.main.forms import CreateGameForm
from Scrabble.models import User, Invite, Game, Board, Chat
from Scrabble.utils import TileFetcher, util_playWord, util_swap, getUsername, sendInviteEmail
import json
import hashlib
import os


def generate_cache_buster(file_path):
    with open(file_path, 'rb') as f:
        return hashlib.md5(f.read()).hexdigest()


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
        user = User(username=form.username.data, email=form.email.data)
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
        if player2 == 1:
            # The AI account
            invite2 = Invite(user_id=player2, game_id=found_game.id, accepted=True)
            found_game.refillBank(2)
        else:
            invite2 = Invite(user_id=player2, game_id=found_game.id, accepted=False)
            
        db.session.add(invite2)

        db.session.commit()

        if user2.id != 1:
            # Don't email the Bot
            sendInviteEmail(user2.username, getUsername(player1))

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
    
    # Log out board state
    #log = {
    #    'board':board.data['rows'],
    #    'bonuses': {'#':'Double letter value',
    #                '@':'Triple letter value',
    #                '%':'Double word value',
    #                '$':'Triple word value'},
    #    'bank': list(bankstr)
    #}
    #current_app.logger.debug(json.dumps(log))

    return render_template('board.html', board=board, tiles=tileFetcher, bank=bank)



@bp.route('/playWord', methods=['POST'])
@login_required
def playWord():
    board_id = request.values.get('board_id')
    attempt = json.loads(request.values.get('attempt'))

    rv = util_playWord(current_user.id, board_id, attempt)

    # return json to the client
    return rv


@bp.route('/swapTiles', methods=['POST'])
@login_required
def swapTiles():
    board_id = request.values.get('board_id')
    swap = json.loads(request.values.get('swap'))
    word = ''.join(swap)

    rv = util_swap(current_user.id, board_id, word)

    return rv


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

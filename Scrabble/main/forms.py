from flask_wtf import FlaskForm
from flask_login import current_user
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.validators import ValidationError, DataRequired, EqualTo, Length
from Scrabble.models import User

class LoginForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired()])
    password = PasswordField('Password', validators=[DataRequired()])
    submit = SubmitField('Log In')

class SignupForm(FlaskForm):
    username = StringField('Username', validators=[DataRequired(), Length(max=64)])
    password = PasswordField('Password', validators=[DataRequired(), Length(max=64)])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Sign Up')

    def validate_username(self, username):
        user = User.query.filter_by(username=username.data).first()
        if user is not None:
            raise ValidationError('Username is already taken')
        if not username.data.isalpha():
            raise ValidationError('Username must consist of letters only')
        if len(username.data) > 8:
            raise ValidationError('Username must be 8 chars or fewer')

class CreateGameForm(FlaskForm):
    name = StringField('Nickname for this game', validators=[DataRequired(), Length(max=64)])
    opponent = StringField('Opponent\'s username', default='Colin', validators=[DataRequired(), Length(max=64)])
    random = BooleanField('Randomize this board?')
    submit = SubmitField('Create Game')

    def validate_opponent(self, opp):
        user = User.query.filter_by(username=opp.data).first()
        if user is None:
            raise ValidationError('Opponent username not found')
        elif user.username == current_user.username:
            raise ValidationError('You cannot play yourself. Get a friend to join!')

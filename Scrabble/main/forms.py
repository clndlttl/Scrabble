from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, SelectField, BooleanField
from wtforms.validators import ValidationError, DataRequired, Email, EqualTo, Length
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

class ResetPasswordForm(FlaskForm):
    password = PasswordField('Password', validators=[DataRequired()])
    password2 = PasswordField(
        'Repeat Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Reset Password')

class CreateGameForm(FlaskForm):
    name = StringField('Nickname for this game', validators=[DataRequired(), Length(max=64)])
    select1 = SelectField('Opponent #1', validators=[DataRequired()])
    select2 = SelectField('Opponent #2')
    select3 = SelectField('Opponent #3')
    random = BooleanField('Randomize this board?')
    submit = SubmitField('Create Game')

    def validate_select1(self, sel):
        if sel.data == '0':
            raise ValidationError('Must have a second player') 

    def validate_select2(self, sel):
        if int(sel.data) > 0 and sel.data == self.select1.data:
            raise ValidationError('Opponent is redundant')

    def validate_select3(self, sel):
        if int(sel.data) > 0 and sel.data == self.select2.data:
            raise ValidationError('Opponent is redundant')

    def populate_users(self, thisuser):
        users = User.query.all()
        choices = [(u.id,u.username) for u in users if u.id != thisuser]
        choices.insert(0,(0,'nobody'))
        choices.insert(0,(-1,'anybody'))
        self.select1.choices = choices
        self.select2.choices = choices
        self.select3.choices = choices




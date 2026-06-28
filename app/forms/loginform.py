from flask_wtf import FlaskForm
from wtforms import PasswordField, BooleanField, SubmitField, EmailField
from wtforms.validators import DataRequired

class LoginForm(FlaskForm):
    email = EmailField(('Email address'), validators=[DataRequired()])
    password = PasswordField(('Password'), validators=[DataRequired()])
    remember_me = BooleanField(('Remember Me'))
    submit = SubmitField(('Sign in'))
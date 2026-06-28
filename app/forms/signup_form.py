from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, EmailField, SelectField
from wtforms.validators import DataRequired, EqualTo, ValidationError, Email
from app.config import db
from app.models import User
from sqlalchemy import Select

class SignupForm(FlaskForm):
    username = StringField(('Username'), validators=[DataRequired()])
    email = EmailField(('Email address'), validators=[DataRequired(), Email()])
    password = PasswordField(('Password'), validators=[DataRequired()])
    confirm_password = PasswordField(('Confirm Password'), validators=[DataRequired(),
                                                                    EqualTo('password')])
    role = SelectField(
        ('Role'), 
        choices=[
            ('User', 'User') , 
            ('Admin', 'Admin')], 
            validators=[DataRequired()]
    )
    activate_user_account_by = SelectField(
        'Activate account after registration by?',
        choices=[
            ('Email', 'Email') , 
            ('SMS', 'SMS')], 
            validators=[DataRequired()]
    )
    user_phone_number = StringField(
        ('Phone number (required if you want to activate account by SMS) country code followed by phone number, e.g. +1234567890'),
    )
    submit = SubmitField(('Register'))

    def validate_username(self, username):
        user = db.session.scalar(Select(User).where(User.user_name == username.data))
        if user is not None:
            raise ValidationError(('Please use a different username'))
    
    def validate_email(self, email):
        user = db.session.scalar(Select(User).where(User.user_email == email.data))
        if user is not None:
            raise ValidationError(('Please use a different email address'))
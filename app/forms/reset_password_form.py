from flask_wtf import FlaskForm
from wtforms import SubmitField, PasswordField
from wtforms.validators import DataRequired, EqualTo

class ResetPasswordForm(FlaskForm):
    password = PasswordField(('Password'), validators=[DataRequired()])
    confirm_password = PasswordField(
            ('Confirm_Password'), validators=[DataRequired(), EqualTo('password')]
    )
    submit = SubmitField(('Request Password Reset'))
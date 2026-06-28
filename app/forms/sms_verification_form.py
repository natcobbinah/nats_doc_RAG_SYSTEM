from flask_wtf import FlaskForm
from wtforms import  IntegerField, StringField, SubmitField
from wtforms.validators import DataRequired

class SMSVerificationForm(FlaskForm):
    phone_number = StringField(('Phone Number'), validators=[DataRequired()])
    sms_code = StringField(('SMS Code'), validators=[DataRequired()])
    submit = SubmitField(('Verify SMS Code'))
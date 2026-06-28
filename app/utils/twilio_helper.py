from flask import current_app
from app.models import VerificationServiceSID
from app.config import db
from twilio.rest import Client
from datetime import datetime, timedelta
from app.logging_utils import log, LogLevel
from threading import Thread

def send_async_sms(app, message, client) -> None:
    with app.app_context():
        client.messages.create(
            body=message["body"],
            from_=message["from_"],
            to=message["to"]
        )
      
def send_sms(user_phone_number, message_body) -> None:
    log(type=LogLevel.INFO, message=f"Preparing to send SMS to {user_phone_number} with body: {message_body}")

    ACCOUNT_SID = current_app.config["TWILIO_ACCOUNT_SID"]
    AUTH_TOKEN = current_app.config["TWILIO_ACCOUNT_AUTH_TOKEN"]
    PHONE_NUMBER = current_app.config["TWILIO_PHONE_NUMBER"]

    client = Client(ACCOUNT_SID, AUTH_TOKEN)

    message = {
        "body": message_body,
        "from_": PHONE_NUMBER,
        "to": user_phone_number
    }
    app = current_app._get_current_object()
    Thread(target=send_async_sms, args=(app, message, client)).start()
    log(type=LogLevel.INFO, message=f"Sent SMS to {user_phone_number}: {message_body}")
      
def send_async_verification(app, sms_initialization_data, client) -> None:
    with app.app_context():
        verification_created = client\
                            .verify\
                            .services(sms_initialization_data["verification_service_sid"])\
                            .verifications\
                            .create(to=sms_initialization_data["user_phone_number"], channel="sms")
    log(type=LogLevel.INFO, message=f"Sent verification token to {sms_initialization_data['user_phone_number']} via SMS")  
    

def verify_sms_token(user_phone_number):
    log(type=LogLevel.INFO, message=f"Initiating SMS verification for {user_phone_number}")

    ACCOUNT_SID = current_app.config["TWILIO_ACCOUNT_SID"]
    AUTH_TOKEN = current_app.config["TWILIO_ACCOUNT_AUTH_TOKEN"]
    client = Client(ACCOUNT_SID, AUTH_TOKEN)

    # get verification service sid from db
    verification_service_sid = VerificationServiceSID.query.first() 
    app = current_app._get_current_object()

    sms_initialization_data = {
        "verification_service_sid": verification_service_sid.sid,
        "user_phone_number": user_phone_number,
    }

    Thread(target=send_async_verification, args=(app, sms_initialization_data, client)).start()

def check_verified_sms_token(user_phone_number, token):
    log(type=LogLevel.INFO, message=f"Checking SMS verification token for {user_phone_number}")

    ACCOUNT_SID = current_app.config["TWILIO_ACCOUNT_SID"]
    AUTH_TOKEN = current_app.config["TWILIO_ACCOUNT_AUTH_TOKEN"]
    client = Client(ACCOUNT_SID, AUTH_TOKEN)

    # get verification service sid from db
    verification_service_sid = VerificationServiceSID.query.first() 

    verification_check = client\
                            .verify\
                            .services(verification_service_sid.sid)\
                            .verification_checks\
                            .create(to=user_phone_number, code=token)

    log(type=LogLevel.INFO, message=f"Verification check status: {verification_check.status}")
    return verification_check.status
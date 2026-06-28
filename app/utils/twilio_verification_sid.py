from app.config import db
from app.models import VerificationServiceSID
from twilio.rest import Client
from flask import current_app
from app.logging_utils import log, LogLevel

def generate_twilio_verification_service_sid():
    log(type=LogLevel.INFO, message=f"Generating Twilio verification service SID and storing in database")
    
    """Generate a Twilio verification service SID and store it in the database."""
    ACCOUNT_SID = current_app.config["TWILIO_ACCOUNT_SID"]
    AUTH_TOKEN = current_app.config["TWILIO_ACCOUNT_AUTH_TOKEN"]
    PHONE_NUMBER = current_app.config["TWILIO_PHONE_NUMBER"]
    client = Client(ACCOUNT_SID, AUTH_TOKEN)

    # create a verification service and store in db, as we will use it to 
    # verify the token later.
    verification = client.verify.services.create(friendly_name="Nats_Doc_Rag_System")    
    
    # check db if verification service sid already exists, if not create and store in db
    existing_verification_service_sid = VerificationServiceSID.query.first()
    if not existing_verification_service_sid:
        verification_sid = VerificationServiceSID(sid=verification.sid)
        db.session.add(verification_sid)
        db.session.commit()
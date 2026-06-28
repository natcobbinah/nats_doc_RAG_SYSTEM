from app.config import db
from app.models.oauth.resource_owner import user_roles, RoleName


class VerificationServiceSID(db.Model):
    __tablename__ = "sms_verification_service_sid"

    id = db.Column(db.Integer, primary_key=True)
    sid = db.Column(db.String(100), unique=True, nullable=False)  

    def __repr__(self):
        return f"<VerificationServiceSID {self.sid}>"
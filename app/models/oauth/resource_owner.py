from app.config import db
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import login_manager, flask_cache
import jwt
from time import time
from datetime import datetime
from flask import current_app
import enum
import json

class RoleName(enum.Enum):
    USER = "User"
    ADMIN = "Admin"

# Association table for many-to-many User <--> Role
user_roles = db.Table(
    "user_roles",
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("role_id", db.Integer, db.ForeignKey("role.id"), primary_key=True),
)

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_name = db.Column(db.String(50), index=True)
    user_email = db.Column(db.String(150), index=True, unique=True, nullable=False)
    user_phone_number = db.Column(db.String(20), index=True, unique=True, nullable=True)
    password_hash = db.Column(db.Text, nullable=False)
    active = db.Column(db.Boolean, default=False, nullable=False)

    # Many-to-many relationship with Role
    roles = db.relationship(
        "Role",
        secondary=user_roles,
        back_populates="users"
    )

    def has_role(self, role_name: RoleName) -> bool:
        """Check if user has a given role"""
        return any(role.name == role_name for role in self.roles)

    def __str__(self):
        return self.user_name

    # override Flask-Login is_active so that, the user has to activate their account
    # before it can be used
    def is_active(self):
        return self.active

    def get_user_id(self):
        return self.id
    
    def get_user_email(self):
        return self.user_email
    
    def get_user_name(self):
        return self.user_name

    def set_user_phone_number(self, phone_number):
        self.user_phone_number = phone_number
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def get_reset_password_token(self, expires_in=600):
        return jwt.encode({
            'reset_password': self.id, 'exp': time() + expires_in
        },
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )

    @staticmethod
    def verify_reset_password_token(token):
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'],
                            algorithms=['HS256'])['reset_password']
        except:
            return 
        return User.query.get(id)

    
    def get_activate_user_account_token(self, expires_in=600):
        return jwt.encode({
            'activate_user_account': self.id, 'exp': time() + expires_in
        },
            current_app.config['SECRET_KEY'],
            algorithm='HS256'
        )

    @staticmethod
    def verify_activate_user_account_token(token):
        try:
            id = jwt.decode(token, current_app.config['SECRET_KEY'],
                            algorithms=['HS256'])['activate_user_account']
        except:
            return 
        return User.query.get(id)

@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))
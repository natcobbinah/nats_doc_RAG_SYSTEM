from app.models import User, Role, RoleName
from app.config import db
from app.utils.email import send_user_account_activation_email

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app
)
from werkzeug.exceptions import HTTPException
from app.utils import generate_password
from app.extensions import oauth
from flask_login import login_user
from sqlalchemy import Select
from app.logging_utils import log, LogLevel
from urllib.parse import urlparse

google_auth_bp = Blueprint('google_auth_route', __name__, url_prefix='/google_auth')

AUTH_LOGIN_TEMPLATE = 'user/auth/login.html'
AUTH_SIGNUP_TEMPLATE = 'user/auth/signup.html'

ERROR_404_TEMPLATE = 'errors/error_404.html'
ERROR_500_TEMPLATE = 'errors/error_500.html'


# error handlers
@google_auth_bp.app_errorhandler(404)
def not_found_error(error):
    log(type=LogLevel.ERROR, message=f"{error}")

    return render_template(ERROR_404_TEMPLATE, error=error), 404


@google_auth_bp.app_errorhandler(Exception)
def internal_error(error):
    if isinstance(error, HTTPException):
        return error

    log(type=LogLevel.ERROR, message=f"{error}")
    # rollback any database operation before exception occured
    db.session.rollback()

    # handle non-HTTP exceptions only
    return render_template(ERROR_500_TEMPLATE, error=error), 500


# login user account using google
@google_auth_bp.route("/login")
def login():
    log(type=LogLevel.INFO, message=f"Accessing Google login route")

    redirect_uri = url_for("google_auth_route.authorize", _external=True)
    return oauth.google.authorize_redirect(redirect_uri)

@google_auth_bp.route("/authorize")
def authorize():
    log(type=LogLevel.INFO, message=f"Accessing Google authorize route")
    
    token = oauth.google.authorize_access_token()

    userdata = {
        'email': token['userinfo']['email'],
        'name': token['userinfo']['name']
    }

    # If user email exists login user to their dashboard
    user = db.session.scalar(
        Select(User).where(User.user_email == userdata["email"])
    )

    if user and user.is_active():
        login_user(user)
        
        # if a user has role USER and AGENT, you can decide where to redirect them based on your application logic
        if user.has_role(RoleName.USER):
            return redirect(url_for('user_dashboard_route.dashboard'))
        return  redirect(url_for('agents_dashboard_route.dashboard'))
    
    else:
        # create user account, let them activate it, and then redirect them to their dashboard
        default_password = generate_password()
        new_user = User(user_name=userdata["name"], user_email=userdata["email"], active=False)
        new_user.set_password(default_password)
        db.session.add(new_user)

        # assign role to user
        user_role = Role.query.filter_by(name=RoleName.USER).first()
        new_user.roles.append(user_role)

        db.session.commit()
        
        # send email to user to activate their account
        send_user_account_activation_email(new_user, social_acccount_signup_default_password=default_password)
        
        flash('Registration completed successfully. Check your email to activate your account', category='success')
        
        return redirect(url_for('auth_route.registration_completed'))
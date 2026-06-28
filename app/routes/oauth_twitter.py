from app.models import User, Role, RoleName
from app.config import db
import requests
import jwt
from app.utils import generate_password
from app.logging_utils import log,LogLevel
from app.utils.email import send_user_account_activation_email

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app
)
from werkzeug.exceptions import HTTPException
from app.extensions import oauth
from sqlalchemy import Select
from flask_login import login_user

twitter_auth_bp = Blueprint('twitter_auth_route', __name__, url_prefix='/twitter_auth')

AUTH_LOGIN_TEMPLATE = 'user/auth/login.html'
AUTH_SIGNUP_TEMPLATE = 'user/auth/signup.html'

ERROR_404_TEMPLATE = 'errors/error_404.html'
ERROR_500_TEMPLATE = 'errors/error_500.html'

# error handlers
@twitter_auth_bp.app_errorhandler(404)
def not_found_error(error):
    log(type=LogLevel.ERROR, message=f"{error}")
    return render_template(ERROR_404_TEMPLATE, error=error), 404

@twitter_auth_bp.app_errorhandler(Exception)
def internal_error(error):
    if isinstance(error, HTTPException):
        return error

    log(type=LogLevel.ERROR, message=f"{error}")
    # rollback any database operation before exception occured
    db.session.rollback()

    # handle non-HTTP exceptions only
    return render_template(ERROR_500_TEMPLATE, error=error), 500

# login user account using twiter
@twitter_auth_bp.route("/login")
def login():
    redirect_uri = url_for('twitter_auth_route.authorize', _external=True)
    log(type=LogLevel.INFO, message=f"redirecturl = {redirect_uri}")
    return oauth.twitter.authorize_redirect(redirect_uri)

@twitter_auth_bp.route("/authorize")
def authorize():
    log(type=LogLevel.INFO, message=f"Accessing Twitter authorize route")

    # Twitter redirects here after user authorizes
    token = oauth.twitter.authorize_access_token()

    log(type=LogLevel.INFO, message=f"token = {token}")

    # Fetch user profile  
    user_info_plus_email = current_app.config["TWITTER_OAUTH2_ACCESS_USERDATA_URL"] + "?user.fields=confirmed_email"

    resp = oauth.twitter.get(user_info_plus_email)
    user_info = resp.json()

    userdata= {
        "id": user_info["data"]["id"],
        "username": user_info["data"]["username"],
        "name": user_info["data"]["name"],
        "email": user_info["data"]["confirmed_email"],
    }

    log(type=LogLevel.INFO, message=f"userinfo = {user_info}")

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
        log(type=LogLevel.INFO, message=f"Creating new user account for {userdata['email']}")
        # create user account, let them activate it, and then redirect them to their dashboard
        default_password = generate_password()
        new_user = User(user_name=userdata["name"], user_email=userdata["email"], active=False)
        new_user.set_password(default_password)
        db.session.add(new_user)

        # assign role to user
        user_role = Role.query.filter_by(name=RoleName.USER).first()
        new_user.roles.append(user_role)

        db.session.commit()
        
        log(type=LogLevel.INFO, message=f"User account created for {userdata['email']}. Sending account activation email.")

        # send email to user to activate their account
        send_user_account_activation_email(new_user, social_acccount_signup_default_password=default_password)
        
        log(type=LogLevel.INFO, message=f"Account activation email sent to {userdata['email']}. Redirecting to registration completed page.")

        flash('Registration completed successfully. Check your email to activate your account', category='success')
        
        return redirect(url_for('auth_route.registration_completed'))
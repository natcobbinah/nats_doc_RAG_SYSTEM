from app.models import User, Role, RoleName
from app.config import db
import requests
from app.utils import generate_password
from app.utils.email import send_user_account_activation_email

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for, current_app
)
from werkzeug.exceptions import HTTPException
from app.extensions import github
from sqlalchemy import Select
from flask_login import login_user
from app.logging_utils import log, LogLevel

github_auth_bp = Blueprint('github_auth_route', __name__, url_prefix='/github_auth')

AUTH_LOGIN_TEMPLATE = 'user/auth/login.html'
AUTH_SIGNUP_TEMPLATE = 'user/auth/signup.html'

ERROR_404_TEMPLATE = 'errors/error_404.html'
ERROR_500_TEMPLATE = 'errors/error_500.html'

# error handlers
@github_auth_bp.app_errorhandler(404)
def not_found_error(error):
    return render_template(ERROR_404_TEMPLATE, error=error), 404

@github_auth_bp.app_errorhandler(Exception)
def internal_error(error):
    log(type=LogLevel.ERROR, message=f"{error}")
    if isinstance(error, HTTPException):
        return error

    log(type=LogLevel.ERROR, message=f"{error}")
    # rollback any database operation before exception occured
    db.session.rollback()

    # handle non-HTTP exceptions only
    return render_template(ERROR_500_TEMPLATE, error=error), 500

# login user account using github
@github_auth_bp.route("/login")
def login():
    log(type=LogLevel.INFO, message=f"Accessing GitHub login route")
    return github.authorize()

@github_auth_bp.route("/callback")
def callback():
    log(type=LogLevel.INFO, message=f"Accessing GitHub callback route")
    with requests.Session() as s:
        params = {
            "client_id": current_app.config["GITHUB_CLIENT_ID"],
            "client_secret": current_app.config["GITHUB_CLIENT_SECRET"],
            "code":request.args.get('code')
        }
        headers = {
            'accept': 'application/json'
        }
        github_access_token = s.post( current_app.config["GITHUB_ACCESS_TOKEN_URL"],
              params=params, headers=headers)

        response = github_access_token.json()

        #print(response)
        
        token_info = {
            "access_token": response.get('access_token'), 
            "token_type":  response.get('token_type'),
            "scope": response.get('scope')
        }

        user_github_info = get_user_data(token_info["access_token"], s)
        #print(user_github_info)

        # If user email exists login user to their dashboard
        user = db.session.scalar(
            Select(User).where(User.user_email == user_github_info["email"])
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
            new_user = User(user_name=user_github_info["name"], user_email=user_github_info["email"], active=False)
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

def get_user_data(access_token:str, request_session) ->  dict:
    log(type=LogLevel.INFO, message=f"Fetching user data from GitHub API")
    
    if not access_token is None:
        access_token = 'Bearer ' + access_token
    else:
        return 'Access token cannot be None'

    github_user_url = current_app.config["GITHUB_API_BASE_URL"] + '/user'
    headers = {
        "Authorization": access_token
    }
    response = request_session.get(github_user_url, headers=headers)

    return response.json()
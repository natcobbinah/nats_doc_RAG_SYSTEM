from app.models import User, RoleName, Role
from app.config import db
from app.forms import (
    LoginForm, SignupForm, ResetPasswordRequestForm, ResetPasswordForm,
    SMSVerificationForm
)
from app.extensions import login_manager
from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for,
)
from sqlalchemy.exc import IntegrityError
from urllib.parse import urlparse
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.exceptions import HTTPException
from flask_login import current_user, login_user, logout_user, login_required
from app.utils.email import send_password_reset_email, send_user_account_activation_email
from sqlalchemy import Select
from app.logging_utils import log, LogLevel
from app.utils.twilio_helper import verify_sms_token, check_verified_sms_token
from app.models import VerificationServiceSID

auth_bp = Blueprint('auth_route', __name__, url_prefix='/auth')

AUTH_LOGIN_TEMPLATE = 'user/auth/login.html'
AUTH_REGISTRATION_TEMPLATE = 'user/auth/registration_form.html'
AUTH_REGISTRATION_COMPLETE_TEMPLATE = 'user/auth/registration_complete.html'
AUTH_ACTIVATE_USER_ACCOUNT = 'user/auth/activation_complete.html'
AUTH_RESET_PASSWORD_REQUEST_TEMPLATE = 'user/auth/reset_password_request.html'
AUTH_RESET_PASSWORD_TEMPLATE = 'user/auth/reset_password.html'
SMS_VERIFICATION_TEMPLATE = 'user/auth/sms_verification.html'

ERROR_404_TEMPLATE = 'errors/error_404.html'
ERROR_500_TEMPLATE = 'errors/error_500.html'


# error handlers
@auth_bp.app_errorhandler(404)
def not_found_error(error):
    log(type=LogLevel.INFO, message=f"{error}")
    return render_template(ERROR_404_TEMPLATE, error=error), 404


@auth_bp.app_errorhandler(Exception)
def internal_error(error):
    if isinstance(error, HTTPException):
        log(type=LogLevel.INFO, message=f"{error}")
        return error

    # rollback any database operation before exception occured
    db.session.rollback()

    log(type=LogLevel.INFO, message=f"{error}")
    # handle non-HTTP exceptions only
    return render_template(ERROR_500_TEMPLATE, error=error), 500 


@login_manager.user_loader
def load_user(id):
    return User.query.get(int(id))


@auth_bp.route("/login", methods=('GET', 'POST'))
def login():
    log(type=LogLevel.INFO, message=f"Accessing login page")

    error = None 

    form = LoginForm()

    if form.validate_on_submit():
        user = User.query.filter_by(user_email=form.email.data).first()
        
        if user is None or  not user.check_password(form.password.data):
            error = "Invalid email or password"

            log(type=LogLevel.INFO, message=f"{error}")
            return render_template(AUTH_LOGIN_TEMPLATE, error=error, form=form)
        
        if user and user.check_password(form.password.data):
            if not user.is_active():
                error = "Account not activated. Check your email to activate your account"
                
                log(type=LogLevel.INFO, message=f"{error}")
                return render_template(AUTH_LOGIN_TEMPLATE, error=error, form=form)
            
        login_user(user,remember=form.remember_me.data)

        # if a user tries to access a protected resource and redirected to login
        # before accessing the protected resource the next query parameters added
        # to the urls is handled here
        next_page = request.args.get('next')
        log(type=LogLevel.INFO, message=f"{next_page}")
        
        if not next_page or urlparse(next_page).netloc != '':
            if current_user.has_role(RoleName.USER):
                next_page = url_for('user_dashboard_route.dashboard')
               
            elif current_user.has_role(RoleName.ADMIN):
                next_page = url_for('agents_dashboard_route.dashboard')
        
        return redirect(next_page)

    return render_template(AUTH_LOGIN_TEMPLATE, form=form)
  

@auth_bp.route("/register", methods=('GET', 'POST'))
def register():
    log(type=LogLevel.INFO, message=f"Accessing registration page")

    if current_user.is_authenticated and current_user.is_active and current_user.has_role(RoleName.USER):
        return  redirect(url_for('user_dashboard_route.dashboard'))
    elif current_user.is_authenticated and current_user.is_active and current_user.has_role(RoleName.ADMIN):
        return  redirect(url_for('agents_dashboard_route.dashboard'))

    form = SignupForm()

    if form.validate_on_submit():
        user = User(
            user_name=form.username.data, 
            user_email=form.email.data, 
            active=False
        )
        user.set_password(form.password.data)

        # set user phone number if user provided it in the registration form. This is needed if user chooses to activate their account via SMS
        if form.user_phone_number.data:
            user.set_user_phone_number(form.user_phone_number.data)

        # check to see if user email or username already exists before setting password and adding to database to avoid unnecessary operations
        user_email_check = User.query.filter_by(user_email=form.email.data).first()

        if user_email_check:
            error = "User with email already exists"
            log(type=LogLevel.INFO, message=f"{error}")
            return render_template(AUTH_REGISTRATION_TEMPLATE, form=form, error=error)
            
        user_name_check = User.query.filter_by(user_name=form.username.data).first()
        if user_name_check:
            error = "User with username already exists"
            log(type=LogLevel.INFO, message=f"{error}")
            return render_template(AUTH_REGISTRATION_TEMPLATE, form=form, error=error)

        try:
            # add user to database
            db.session.add(user)
            
            # assign role to user
            if form.role.data == 'User':
                user_role = Role.query.filter_by(name=RoleName.USER).first()
                user.roles.append(user_role)
            elif form.role.data == 'Admin':
                user_role = Role.query.filter_by(name=RoleName.ADMIN).first()
                user.roles.append(user_role)
            
            db.session.commit()

            # based on the user selection of how they want to activate their account send email or sms to activate their account
            if form.activate_user_account_by.data == 'Email':
                send_user_account_activation_email(user)
            elif form.activate_user_account_by.data == 'SMS' and form.user_phone_number.data:
                verification_status = verify_sms_token(form.user_phone_number.data)

                flash('Verification token sent to your phone number. Please verify to activate your account.', category='info')
                log(type=LogLevel.INFO, message=f"Verification token sent to {form.user_phone_number.data}. Please verify to activate your account.")
            
                # redirect user to sms verification page where they can input the token they received on their phone to verify and activate their account
                return redirect(url_for('auth_route.sms_verification',  user_phone_number=form.user_phone_number.data))

            else:
                flash('Invalid activation method or phone number. Please try again.', category='danger')
                return render_template(AUTH_REGISTRATION_TEMPLATE, form=form)

            flash('Registration completed successfully. Check your email to activate your account', category='success')
            
            log(type=LogLevel.INFO, message="Registration completed successfully. Check your email to activate your account")
            return redirect(url_for('auth_route.registration_completed'))
        except IntegrityError:
            db.session.rollback()

            log(type=LogLevel.INFO, message="Integrity error")
            flash("Username or email already exists.", "danger")
        except Exception as e:

            log(type=LogLevel.INFO, message=f"{e}")
            db.session.rollback()


    return render_template(AUTH_REGISTRATION_TEMPLATE, form=form)


@auth_bp.route('/register/complete')
def registration_completed():
    log(type=LogLevel.INFO, message=f"Accessing registration completed page")

    return render_template(AUTH_REGISTRATION_COMPLETE_TEMPLATE)


@auth_bp.route('/logout')
@login_required
def logout():
    log(type=LogLevel.INFO, message=f"User {current_user.user_email} logged out")
    
    logout_user()
    return redirect(url_for('home_route.home'))

@auth_bp.route('/reset_password_request', methods=('GET', 'POST'))
def reset_password_request():
    log(type=LogLevel.INFO, message=f"Accessing password reset request page")

    if current_user.is_authenticated and current_user.is_active:
        if current_user.has_role(RoleName.USER):
            return  redirect(url_for('dashboard_route.dashboard'))
        elif current_user.has_role(RoleName.ADMIN):
            return  redirect(url_for('agent_dashboard_route.dashboard'))

    form = ResetPasswordRequestForm()

    if form.validate_on_submit():
        user = db.session.scalar(
            Select(User).where(User.user_email == form.email.data)
        )
        
        if user:
            send_password_reset_email(user)
            flash('Check your email for the instructions to reset your password', category='success')
            return redirect(url_for('auth_route.login'))
    
    return render_template(AUTH_RESET_PASSWORD_REQUEST_TEMPLATE, form=form)

# reset user password
@auth_bp.route('/reset_password/<token>', methods=('GET', 'POST'))
def reset_password(token):
    log(type=LogLevel.INFO, message=f"Accessing password reset page")

    if current_user.is_authenticated and current_user.is_active:
        if current_user.has_role(RoleName.USER):
            return  redirect(url_for('dashboard_route.dashboard'))
        elif current_user.has_role(RoleName.ADMIN):
            return  redirect(url_for('agent_dashboard_route.dashboard'))
    
    user = User.verify_reset_password_token(token)

    if not user:
        return redirect(url_for('home_route.home'))

    form = ResetPasswordForm()

    if form.validate_on_submit():

        user.set_password(form.password.data)
        db.session.commit()
        log(type=LogLevel.INFO, message=f"User {user.user_email} has reset their password successfully")

        flash('Your password has been reset', category='success')
        return redirect(url_for('auth_route.login'))
    return render_template(AUTH_RESET_PASSWORD_TEMPLATE, form=form, token=token,
                           email=user.get_user_email())


# activate user account
@auth_bp.route('/active/<token>', methods=('GET', 'POST'))
def activate_user_account(token):
    log(type=LogLevel.INFO, message=f"Accessing account activation page")

    if current_user.is_authenticated and current_user.is_active and current_user.has_role(RoleName.USER):
        return  redirect(url_for('user_dashboard_route.dashboard'))
    elif current_user.is_authenticated and current_user.is_active and current_user.has_role(RoleName.ADMIN):
        return  redirect(url_for('agents_dashboard_route.dashboard'))
    
    user = User.verify_activate_user_account_token(token)

    if not user:
        return redirect(url_for('home_route.home'))
    
    if user:
        user.active = True 
        db.session.commit()

        log(type=LogLevel.INFO, message=f"User {user.user_email} has activated their account successfully")

        flash('Your user account has been activated successfully', category='success')
        return redirect(url_for('auth_route.activate_user_account_completed', email=user.get_user_email()))
        #return render_template(AUTH_ACTIVATE_USER_ACCOUNT, email=user.get_user_email())


# user account activation completed
@auth_bp.route('/active/complete')
def activate_user_account_completed():
    log(type=LogLevel.INFO, message=f"Accessing account activation completed page")
    
    return render_template(AUTH_ACTIVATE_USER_ACCOUNT, email=request.args.get('email'))

@auth_bp.route('/sms_verification', methods=('GET', 'POST'))
def sms_verification():
    log(type=LogLevel.INFO, message=f"Accessing SMS verification page")
    # this route is where user is redirected to after they choose to activate their account. 
    # on this page they can input the token they received on their phone to verify and activate their account
    user_phone_number = request.args.get('user_phone_number')

    form = SMSVerificationForm()

    if form.validate_on_submit():
        verification_status = check_verified_sms_token(form.phone_number.data, form.sms_code.data)

        log(type=LogLevel.INFO, message=f"Verification status for phone number {form.phone_number.data}: {verification_status}")

        if verification_status == "approved":
            # activate user account
            user = db.session.scalar(
                Select(User).where(User.user_phone_number == form.phone_number.data)
            )

            if user:
                user.active = True 
                db.session.commit()
                
                log(type=LogLevel.INFO, message=f"User with phone number {form.phone_number.data} has activated their account successfully")

                flash('Your user account has been activated successfully', category='success')
                return redirect(url_for('auth_route.activate_user_account_completed', email=user.get_user_email()))
        else:
            flash('Invalid or expired SMS code. Please try again.', category='danger') 
    
    return render_template(SMS_VERIFICATION_TEMPLATE, form=form, user_phone_number=user_phone_number)
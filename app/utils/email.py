from flask_mail import Message
from app.extensions import mail
from flask import current_app, render_template
from app.models import RoleName
from threading import Thread
from app.logging_utils import log, LogLevel

EMAIL_TXT_RESET_TEMPLATE = "email/reset_password.txt"
EMAIL_HTML_RESET_TEMPLATE = "email/reset_password.html"

USER_ACCOUNT_TXT_ACTIVATE_TEMPLATE = "email/activate_user_account.txt"
USER_ACCOUNT_EMAIL_ACTIVATE_TEMPLATE = "email/activate_user_account.html"


def send_async_email(app, msg):
    with app.app_context():
        mail.send(msg)

def send_email(subject, sender, recipients, text_body, html_body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.body = text_body
    msg.html = html_body
    #mail.send(msg)
    log(type=LogLevel.INFO, message=f"Sending email to {recipients} with subject '{subject}'")
    app = current_app._get_current_object()
    Thread(target=send_async_email, args=(app,msg)).start()


def send_password_reset_email(user):
    log(type=LogLevel.INFO, message=f"Sending password reset email to {user.user_email}")
    
    token = user.get_reset_password_token()

    send_email(
        "[ Flask OAuth + OTP Demo ] - Reset Your Password",
        sender=current_app.config["MAIL_USERNAME"],
        recipients=[user.user_email],
        text_body=render_template(EMAIL_TXT_RESET_TEMPLATE, user=user, token=token),
        html_body=render_template(EMAIL_HTML_RESET_TEMPLATE, user=user, token=token),
    )


def send_user_account_activation_email(user, 
        social_acccount_signup_default_password=None,
        role=None
    ):
    log(type=LogLevel.INFO, message=f"Sending account activation email to {user.user_email}")

    token = user.get_activate_user_account_token()

    if not social_acccount_signup_default_password is None:
        send_email(
            "[ Flask OAuth + OTP Demo ] - Activate your Flask OAuth + OTP Demo Account",
            sender=current_app.config["MAIL_USERNAME"],
            recipients=[user.user_email],
            text_body=render_template(USER_ACCOUNT_TXT_ACTIVATE_TEMPLATE, user=user, token=token, provided_password=social_acccount_signup_default_password),
            html_body=render_template(USER_ACCOUNT_EMAIL_ACTIVATE_TEMPLATE, user=user, token=token, provided_password=social_acccount_signup_default_password),
        )
    else:
        send_email(
            "[ Flask OAuth + OTP Demo ] - Activate your Flask OAuth + OTP Demo Account",
            sender=current_app.config["MAIL_USERNAME"],
            recipients=[user.user_email],
            text_body=render_template(USER_ACCOUNT_TXT_ACTIVATE_TEMPLATE, user=user, token=token) if role is None else (
                render_template(AGENT_ACCOUNT_TXT_ACTIVATE_TEMPLATE, user=user, token=token)
            ),
            html_body=render_template(USER_ACCOUNT_EMAIL_ACTIVATE_TEMPLATE, user=user, token=token) if role is None else (
                render_template(AGENT_ACCOUNT_EMAIL_ACTIVATE_TEMPLATE, user=user, token=token)
            ),
        )
    return 'Default password need to be provided for social registration'
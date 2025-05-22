import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.core.config import settings
from string import Template
import os

def send_reset_code_email(to_email: str, code: str, reset_token: str):
    # Read the HTML template
    template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'mail.html')
    with open(template_path, 'r', encoding='utf-8') as file:
        html_template = file.read()

    # Substitute variables in the template
    html_content = Template(html_template).substitute(
        email=to_email,
        verification_code=code
    )

    # Create email
    msg = MIMEMultipart()
    msg['From'] = settings.EMAIL_DEFAULT_SENDER
    msg['To'] = to_email
    msg['Subject'] = "Code de réinitialisation de mot de passe"
    msg.attach(MIMEText(html_content, 'html'))

    try:
        # Use SSL for Gmail
        if settings.EMAIL_USE_SSL:
            server = smtplib.SMTP_SSL(settings.EMAIL_HOST, settings.EMAIL_PORT)
        else:
            server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
            server.starttls()

        server.login(settings.EMAIL_SENDER, settings.EMAIL_PASSWORD)
        server.sendmail(settings.EMAIL_DEFAULT_SENDER, to_email, msg.as_string())
        server.quit()
    except Exception as e:
        raise Exception(f"Failed to send email: {str(e)}")


def send_registration_code_email(to_email: str, code: str, verification_token: str):
    template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'registration_verification.html')
    with open(template_path, 'r', encoding='utf-8') as file:
        html_template = file.read()

    html_content = Template(html_template).substitute(
        email=to_email,
        verification_code=code
    )

    msg = MIMEMultipart()
    msg['From'] = settings.EMAIL_DEFAULT_SENDER
    msg['To'] = to_email
    msg['Subject'] = "Code de vérification d'inscription"
    msg.attach(MIMEText(html_content, 'html'))

    try:
        if settings.EMAIL_USE_SSL:
            server = smtplib.SMTP_SSL(settings.EMAIL_HOST, settings.EMAIL_PORT)
        else:
            server = smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT)
            server.starttls()

        server.login(settings.EMAIL_SENDER, settings.EMAIL_PASSWORD)
        server.sendmail(settings.EMAIL_DEFAULT_SENDER, to_email, msg.as_string())
        server.quit()
    except Exception as e:
        raise Exception(f"Failed to send email: {str(e)}")
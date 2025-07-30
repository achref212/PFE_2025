import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from app.core.config import settings
import logging
import dns.resolver

logger = logging.getLogger(__name__)


class EmailNotExistError(Exception):
    """Custom exception for when the email address does not exist."""
    pass


def verify_email_existence(to_email: str) -> bool:
    """Verify if the email address exists by checking DNS MX records and SMTP response."""
    try:
        # Extract domain from email
        domain = to_email.split('@')[1]

        # Check DNS MX records
        try:
            mx_records = dns.resolver.resolve(domain, 'MX')
            if not mx_records:
                logger.error(f"No MX records found for domain: {domain}")
                return False
        except (dns.resolver.NXDOMAIN, dns.resolver.NoAnswer, dns.resolver.NoNameservers):
            logger.error(f"Domain {domain} does not exist or has no mail server")
            return False

        # SMTP verification
        mx_host = mx_records[0].exchange.to_text()
        with smtplib.SMTP(timeout=10) as server:
            server.set_debuglevel(0)
            server.connect(mx_host)
            server.helo(server.local_hostname)
            server.mail(settings.EMAIL_DEFAULT_SENDER)
            code, message = server.rcpt(to_email)
            server.quit()
            if code >= 400:
                logger.error(f"SMTP rejected recipient {to_email}: {message}")
                return False
        return True
    except (smtplib.SMTPConnectError, smtplib.SMTPException) as e:
        logger.error(f"SMTP verification failed for {to_email}: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error during email verification for {to_email}: {str(e)}")
        return False


def send_registration_code_email(to_email: str, code: str, verification_token: str):
    # Verify email existence before proceeding
    if not verify_email_existence(to_email):
        raise EmailNotExistError(f"Cet email n'existe pas: {to_email}")

    template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'registration_verification.html')
    if not os.path.exists(template_path):
        logger.error(f"Template file not found at: {template_path}")
        raise Exception(f"Template file not found at: {template_path}")

    with open(template_path, 'r', encoding='utf-8') as file:
        html_template = file.read()
        logger.debug(f"Raw template: {html_template}")

    html_content = html_template.replace('{{ verification_code }}', code).replace('{{ email }}', to_email)
    logger.debug(f"Substituted content: {html_content}")

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
        return True
    except smtplib.SMTPAuthenticationError as e:
        raise Exception(
            f"SMTP authentication failed: Invalid username or password. Please check EMAIL_SENDER and EMAIL_PASSWORD.")
    except smtplib.SMTPException as e:
        raise Exception(f"SMTP error: {str(e)}")
    except Exception as e:
        raise Exception(f"Failed to send email: {str(e)}")


def send_reset_code_email(to_email: str, code: str, reset_token: str):
    # Verify email existence before proceeding
    if not verify_email_existence(to_email):
        raise EmailNotExistError(f"Cet email n'existe pas: {to_email}")

    template_path = os.path.join(os.path.dirname(__file__), '..', 'templates', 'mail.html')
    if not os.path.exists(template_path):
        logger.error(f"Template file not found at: {template_path}")
        raise Exception(f"Template file not found at: {template_path}")

    with open(template_path, 'r', encoding='utf-8') as file:
        html_template = file.read()
        logger.debug(f"Raw template: {html_template}")

    html_content = html_template.replace('{{ verification_code }}', code).replace('{{ email }}', to_email)
    logger.debug(f"Substituted content: {html_content}")

    msg = MIMEMultipart()
    msg['From'] = settings.EMAIL_DEFAULT_SENDER
    msg['To'] = to_email
    msg['Subject'] = "Code de réinitialisation de mot de passe"
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
        return True
    except smtplib.SMTPAuthenticationError as e:
        raise Exception(
            f"SMTP authentication failed: Invalid username or password. Please check EMAIL_SENDER and EMAIL_PASSWORD.")
    except smtplib.SMTPException as e:
        raise Exception(f"SMTP error: {str(e)}")
    except Exception as e:
        raise Exception(f"Failed to send email: {str(e)}")
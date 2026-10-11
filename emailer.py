import logging
import os
import smtplib
from email.message import EmailMessage

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger('emailer')

# For Gmail, use an App Password (Google Account > Security > 2-Step Verification > App passwords).
SMTP_HOST = os.environ.get('SMTP_HOST', 'smtp.gmail.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', '587'))
SMTP_USER = os.environ.get('SMTP_USER', 'shuraim811@gmail.com')
SMTP_PASSWORD = os.environ.get('SMTP_PASSWORD', 'zasccixbwtmuerne')


def send_email(to_address, subject, body):
    """Send a plain-text email. Returns True on success, False otherwise."""
    if not to_address:
        logger.warning('Email not sent: recipient has no email address.')
        return False
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.warning('Email not sent: SMTP_USER / SMTP_PASSWORD are not set.')
        return False

    message = EmailMessage()
    message['From'] = SMTP_USER
    message['To'] = to_address
    message['Subject'] = subject
    message.set_content(body)

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=10) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.send_message(message)
        return True
    except (smtplib.SMTPException, OSError) as error:
        logger.error('Email to %s failed: %s: %s', to_address, type(error).__name__, error)
        return False

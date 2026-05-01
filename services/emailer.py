"""SMTP email helper for HTML report delivery."""

import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import settings


class EmailService:
    """Send HTML emails using configured SMTP credentials."""

    def send_html(self, recipient: str, subject: str, html_body: str) -> None:
        """Send one HTML email message to recipient."""
        message = MIMEMultipart('alternative')
        message['Subject'] = subject
        message['From'] = settings.SMTP_USER
        message['To'] = recipient
        message.attach(MIMEText(html_body, 'html', 'utf-8'))

        if settings.SMTP_PORT == 465:
            with smtplib.SMTP_SSL(settings.SMTP_HOST, settings.SMTP_PORT) as client:
                client.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
                client.sendmail(settings.SMTP_USER, [recipient], message.as_string())
            return

        with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT) as client:
            client.ehlo()
            client.starttls()
            client.ehlo()
            client.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            client.sendmail(settings.SMTP_USER, [recipient], message.as_string())

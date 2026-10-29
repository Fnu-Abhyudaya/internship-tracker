import os
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email.mime.text import MIMEText
from email import encoders
from datetime import datetime

logger = logging.getLogger(__name__)


def _scan_issue_html(failed_sites):
    """One summary line about websites that could not be scanned."""
    if failed_sites:
        return (
            f'<li style="color: #b91c1c;"><strong>{failed_sites}</strong> '
            f'website(s) could not be scanned properly - see the '
            f'"Scan Issues" sheet</li>'
        )
    return '<li>All websites were scanned without errors</li>'


def _attach_excel(msg, filepath):
    if filepath and os.path.exists(filepath):
        with open(filepath, 'rb') as f:
            part = MIMEBase(
                'application',
                'vnd.openxmlformats-officedocument'
                '.spreadsheetml.sheet'
            )
            part.set_payload(f.read())
            encoders.encode_base64(part)
            part.add_header(
                'Content-Disposition',
                f'attachment; filename="{os.path.basename(filepath)}"'
            )
            msg.attach(part)


def send_email(filepath, recipient, total_jobs, total_companies,
               failed_sites=0):
    smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    smtp_username = os.environ.get('SMTP_USERNAME', '')
    smtp_password = os.environ.get('SMTP_PASSWORD', '')

    if not smtp_username or not smtp_password:
        raise ValueError("SMTP credentials not configured")

    today = datetime.now().strftime('%B %d, %Y')
    msg = MIMEMultipart()
    msg['From'] = smtp_username
    msg['To'] = recipient
    msg['Subject'] = (
        f'Daily Internship Report - {today} '
        f'({total_jobs} new postings)'
    )

    body = f"""
    <html><body style="font-family: Arial, sans-serif;">
        <h2 style="color: #2563eb;">
            Daily Internship Tracker Report
        </h2>
        <p>Date: <strong>{today}</strong></p>
        <hr>
        <h3>Summary</h3>
        <ul>
            <li><strong>{total_jobs}</strong> new internship postings</li>
            <li>From <strong>{total_companies}</strong> companies</li>
            {_scan_issue_html(failed_sites)}
        </ul>
        <p>See the attached Excel file for all details with
           clickable links.</p>
        <hr>
        <p style="color: grey; font-size: 12px;">
            Automated email - Internship Tracker (GitHub Actions)
        </p>
    </body></html>
    """

    msg.attach(MIMEText(body, 'html'))
    _attach_excel(msg, filepath)

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(msg)
        logger.info(f"Email sent to {recipient}")


def send_no_results_email(recipient, filepath=None, failed_sites=0):
    smtp_server = os.environ.get('SMTP_SERVER', 'smtp.gmail.com')
    smtp_port = int(os.environ.get('SMTP_PORT', '587'))
    smtp_username = os.environ.get('SMTP_USERNAME', '')
    smtp_password = os.environ.get('SMTP_PASSWORD', '')

    if not smtp_username or not smtp_password:
        return

    today = datetime.now().strftime('%B %d, %Y')
    msg = MIMEMultipart()
    msg['From'] = smtp_username
    msg['To'] = recipient
    msg['Subject'] = (
        f'Daily Internship Report - {today} (No new postings)'
    )

    body = f"""
    <html><body style="font-family: Arial, sans-serif;">
        <h2>Daily Internship Tracker - {today}</h2>
        <p>No new internship postings were found in the
           last 24 hours.</p>
        <ul>{_scan_issue_html(failed_sites)}</ul>
        <p>The attached Excel file lists any websites that could
           not be scanned.</p>
    </body></html>
    """

    msg.attach(MIMEText(body, 'html'))
    _attach_excel(msg, filepath)

    with smtplib.SMTP(smtp_server, smtp_port) as server:
        server.starttls()
        server.login(smtp_username, smtp_password)
        server.send_message(msg)

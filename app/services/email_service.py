"""
Email service — sends the PDF report to the lead via SMTP.
Sender is always EMAIL_FROM (fixed).
Recipient is leadData.email.
"""
import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger(__name__)


def _env(key: str, default: str = "") -> str:
    return os.getenv(key, default)


def send_report_email(recipient_email: str, first_name: str, full_name: str, pdf_url: str) -> None:
    """
    Send the readiness PDF report to the lead as a tracked download link.
    Clicking the link records 'PDF Opened At' in Google Sheets.
    All SMTP config comes from env vars.
    """
    smtp_host = _env("SMTP_HOST", "smtp.gmail.com")
    smtp_port = int(_env("SMTP_PORT", "587"))
    smtp_user = _env("SMTP_USER")
    smtp_password = _env("SMTP_PASSWORD")
    use_tls = _env("SMTP_USE_TLS", "true").lower() in ("true", "1", "yes")
    email_from = _env("EMAIL_FROM")
    from_name = _env("EMAIL_FROM_NAME", "OBOX HR")

    if not email_from:
        raise RuntimeError("EMAIL_FROM env var not set")
    if not smtp_user or not smtp_password:
        raise RuntimeError("SMTP_USER / SMTP_PASSWORD env vars not set")

    sender = f"{from_name} <{email_from}>"

    # Build message
    msg = MIMEMultipart("mixed")
    msg["From"] = sender
    msg["To"] = recipient_email
    msg["Subject"] = f"{first_name}, Your India HR Readiness Report"

    # Body — download link replaces the attachment so opens can be tracked
    body_html = f"""
    <html><body>
      <p>Hi {first_name},</p>
      <p>Thank you for completing the <strong>India HR Readiness Assessment</strong>.</p>
      <p>Your personalized readiness report is ready. Click the button below to download it:</p>
      <p style="margin: 24px 0;">
        <a href="{pdf_url}"
           style="background:#1a56db;color:#ffffff;text-decoration:none;
                  padding:12px 24px;border-radius:6px;font-weight:bold;
                  display:inline-block;">
          Download My Report
        </a>
      </p>
      <p>Our advisory team will review your results and reach out shortly
         with tailored recommendations for your India expansion journey.</p>
      <br/>
      <p>Warm regards,<br/><strong>OBOX HR Team</strong></p>
    </body></html>
    """
    msg.attach(MIMEText(body_html, "html"))

    # Send
    if use_tls:
        with smtplib.SMTP(smtp_host, smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(smtp_user, smtp_password)
            server.sendmail(email_from, recipient_email, msg.as_string())
    else:
        with smtplib.SMTP_SSL(smtp_host, smtp_port) as server:
            server.login(smtp_user, smtp_password)
            server.sendmail(email_from, recipient_email, msg.as_string())

    logger.info(
        "Report email sent | from=%s | to=%s | name=%s", email_from, recipient_email, full_name
    )

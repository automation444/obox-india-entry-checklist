"""
Email service — sends the report email to the lead via Resend.
"""
import logging
import os

import resend

logger = logging.getLogger(__name__)


def send_report_email(recipient_email: str, first_name: str, full_name: str, pdf_url: str) -> None:
    resend.api_key = os.getenv("RESEND_API_KEY", "")
    if not resend.api_key:
        raise RuntimeError("RESEND_API_KEY env var not set")

    email_from = os.getenv("EMAIL_FROM", "automation@oboxhr.com")
    from_name  = os.getenv("EMAIL_FROM_NAME", "OBOX HR")

    body_html = f"""
    <html><body>
      <p>Hi {first_name},</p>
      <p>Thank you for taking the <strong>India HR Readiness Assessment</strong>.</p>
      <p>Your personalized readiness report is now ready to download.</p>
      <p>It is designed to help you understand your current readiness, highlights the areas that may need attention, and helps you identify which areas could require closer attention as you plan, establish, or scale your operations in India.</p>
      <p style="margin: 24px 0;">
        <a href="{pdf_url}"
           style="background:#1a56db;color:#ffffff;text-decoration:none;
                  padding:12px 24px;border-radius:6px;font-weight:bold;
                  display:inline-block;">
          Download My Report
        </a>
      </p>
      <p>Our advisory team will also review your assessment and share tailored solutions based on your current stage of expansion.</p>
      <br/>
      <p>Thanks & Regards,<br/></p>
      <p>Mahesh Yadav - India Expansion Head<br>+91 773 819 1983 / +91 956 956 0000<br>OBOX HR Solutions | www.oboxhr.com<br>MUMBAI | BANGALORE | HYDERABAD | CHENNAI | DELHI</p>

    </body></html>
    """

    resend.Emails.send({
        "from": f"{from_name} <{email_from}>",
        "to": [recipient_email],
        "subject": f"{first_name}, Your India HR Readiness Report",
        "html": body_html,
    })

    logger.info("Report email sent via Resend | to=%s | name=%s", recipient_email, full_name)


def send_notification_email(full_name: str, email: str, company: str, expansion_stage: str, overall_score: int) -> None:
    resend.api_key = os.getenv("RESEND_API_KEY", "")
    if not resend.api_key:
        raise RuntimeError("RESEND_API_KEY env var not set")

    email_from = os.getenv("EMAIL_FROM", "automation@oboxhr.com")
    from_name  = os.getenv("EMAIL_FROM_NAME", "OBOX HR")
    notify_to  = os.getenv("NOTIFICATION_EMAIL", "mahesh@oboxhr.com")

    body_html = f"""
    <html><body>
      <p>A new India HR Readiness Assessment has been submitted.</p>
      <table style="border-collapse:collapse;margin-top:12px;">
        <tr><td style="padding:6px 16px 6px 0;font-weight:bold;">Name</td><td>{full_name}</td></tr>
        <tr><td style="padding:6px 16px 6px 0;font-weight:bold;">Email</td><td>{email}</td></tr>
        <tr><td style="padding:6px 16px 6px 0;font-weight:bold;">Company</td><td>{company}</td></tr>
        <tr><td style="padding:6px 16px 6px 0;font-weight:bold;">Expansion Stage</td><td>{expansion_stage}</td></tr>
        <tr><td style="padding:6px 16px 6px 0;font-weight:bold;">Overall Score</td><td>{overall_score}%</td></tr>
      </table>
    </body></html>
    """

    resend.Emails.send({
        "from": f"{from_name} <{email_from}>",
        "to": [notify_to],
        "subject": f"New Assessment Submission — {full_name} ({company})",
        "html": body_html,
    })

    logger.info("Notification email sent | lead=%s <%s>", full_name, email)

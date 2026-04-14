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

    resend.Emails.send({
        "from": f"{from_name} <{email_from}>",
        "to": [recipient_email],
        "subject": f"{first_name}, Your India HR Readiness Report",
        "html": body_html,
    })

    logger.info("Report email sent via Resend | to=%s | name=%s", recipient_email, full_name)

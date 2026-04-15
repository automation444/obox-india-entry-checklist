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
      <p>Best regards,<br/></p>
      <table cellpadding=0 cellspacing=0 width=100% style="border-collapse:collapse;width:100%;">
        <tr><td height=0 style="height:0;line-height:1%;padding-top:16px;font-size:1px;"></td></tr>
        <tr><td>
          <table cellpadding=0 cellspacing=0 width=100% style="border-collapse:collapse;width:100%;color:gray;border-top:1px solid gray;line-height:normal;">
            <tr><td height=0 style="height:0;padding:9px 8px 0 0;">
              <p style="color:#888888;text-align:left;font-size:10px;margin:1px;line-height:120%;font-family:Arial">IMPORTANT: The contents of this email and any attachments are confidential. They are intended for the named recipient(s) only. If you have received this email by mistake, please notify the sender immediately and do not disclose the contents to anyone or make copies thereof.</p>
            </td></tr>
          </table>
        </td></tr>
        <tr><td height=0 style="height:0;line-height:1%;padding-top:16px;font-size:1px;"></td></tr>
      </table>
    </body></html>
    """

    resend.Emails.send({
        "from": f"{from_name} <{email_from}>",
        "to": [recipient_email],
        "subject": f"{first_name}, Your India Readiness Report",
        "html": body_html,
    })

    logger.info("Report email sent via Resend | to=%s | name=%s", recipient_email, full_name)

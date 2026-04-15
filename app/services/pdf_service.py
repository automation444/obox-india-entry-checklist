"""
PDF generation service.
Uses Jinja2 to render india-readiness-report.html → WeasyPrint → PDF bytes.
"""
import os
import logging
from datetime import datetime, timezone
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape
from weasyprint import HTML, CSS

from app.models import LeadData
from app.services.scoring import ScoreResult

logger = logging.getLogger(__name__)

TEMPLATES_DIR = Path(__file__).parent.parent / "templates"
ASSETS_DIR = Path(__file__).parent.parent / "assets"


LOGO_FALLBACK_URL = "https://oboxhr.com/assets/images/logo-header.svg"


def _logo_path() -> str:
    """Return file:// URI for the local logo, or the remote URL as fallback."""
    logo = ASSETS_DIR / "OboxLogo.png"
    if logo.exists():
        return logo.as_uri()
    logger.warning("OboxLogo.png not found in assets/; falling back to remote URL")
    return LOGO_FALLBACK_URL


def _build_template_context(lead: LeadData, scores: ScoreResult) -> dict:
    generated_at = datetime.now(timezone.utc)

    sections_ctx = [
        {
            "label": s.label,
            "percent": s.percent,
            "color_class": s.color_class,
        }
        for s in scores.sections
    ]

    return {
        "generated_at": generated_at.strftime("%B %d, %Y"),
        "logo_path": _logo_path(),
        "lead": {
            "name": f"{lead.firstName} {lead.lastName}",
            "email": lead.email,
            "company": lead.company,
            "expansion_stage": lead.expansionStage,
        },
        "scores": {
            "overall": scores.overall,
            "status_text": scores.status_text,
            "status_class": scores.status_class,
            "sections": sections_ctx,
            "weak_sections": scores.weak_sections,
            "risk_areas": scores.risk_areas,
        },
    }


def generate_pdf(lead: LeadData, scores: ScoreResult) -> bytes:
    """Render the Jinja2 template and return PDF bytes."""
    env = Environment(
        loader=FileSystemLoader(str(TEMPLATES_DIR)),
        autoescape=select_autoescape(["html"]),
    )
    template = env.get_template("india-readiness-report.html")
    context = _build_template_context(lead, scores)
    html_string = template.render(**context)

    # CSS is referenced via <link> in the template, but WeasyPrint needs
    # base_url set to the templates dir so it can resolve relative paths.
    pdf_bytes = HTML(
        string=html_string,
        base_url=str(TEMPLATES_DIR),
    ).write_pdf()

    logger.info("PDF generated (%d bytes) for %s", len(pdf_bytes), lead.email)
    return pdf_bytes

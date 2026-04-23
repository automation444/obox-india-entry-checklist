"""
India HR Readiness Assessment — FastAPI backend
POST /api/lead/submit-summary
"""
import logging
import os
import re
import uuid
from types import SimpleNamespace

from dotenv import load_dotenv

load_dotenv()

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response

from app.models import SubmitRequest
from app.services import (
    email_service,
    google_sheets,
    pdf_service,
    scoring,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(title="India HR Readiness Assessment API", version="1.0.0")

# CORS — allow the React/Vite frontend
frontend_origin = os.getenv("FRONTEND_ORIGIN", "http://localhost:8080")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[frontend_origin],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Background worker ──────────────────────────────────────────────────────

def _process_submission(payload: SubmitRequest) -> None:
    """
    Runs in background after the endpoint returns { ok: true }.
    1. Compute scores
    2. Append to Google Sheets (with a unique pdf_token in col N)
    3. Email the lead a tracked download link — no PDF attachment
    """
    lead = payload.leadData
    checklist = payload.assessmentData.readinessChecklist
    checklist_dict = checklist.dict()

    try:
        # 1. Score
        scores = scoring.compute_scores(checklist_dict)
        logger.info(
            "Scores computed | overall=%d | lead=%s %s <%s>",
            scores.overall,
            lead.firstName,
            lead.lastName,
            lead.email,
        )

        # 2. Unique token — ties this submission to its PDF download link
        pdf_token = str(uuid.uuid4())

        # 3. Google Sheets — store token in col N; col O (PDF Opened At) left blank
        timings = payload.assessmentData.sectionTimings
        google_sheets.append_lead_row(
            lead_name=f"{lead.firstName} {lead.lastName}",
            lead_email=lead.email,
            lead_company=lead.company,
            expansion_stage=lead.expansionStage,
            overall_score=scores.overall,
            section1=scores.section1_percent,
            section2=scores.section2_percent,
            section3=scores.section3_percent,
            section4=scores.section4_percent,
            section5=scores.section5_percent,
            risk_areas=scores.risk_areas,
            checklist_dict=checklist_dict,
            pdf_token=pdf_token,
            section_timings=timings,
        )

        # 4. Build the tracked download URL and email it to the lead
        base_url = os.getenv("BACKEND_BASE_URL", "http://localhost:8000").rstrip("/")
        pdf_url = f"{base_url}/api/pdf/{pdf_token}"
        email_service.send_report_email(
            recipient_email=lead.email,
            first_name=lead.firstName,
            full_name=f"{lead.firstName} {lead.lastName}",
            pdf_url=pdf_url,
        )

        email_service.send_notification_email(
            full_name=f"{lead.firstName} {lead.lastName}",
            email=lead.email,
            company=lead.company,
            expansion_stage=lead.expansionStage,
            overall_score=scores.overall,
        )

        logger.info("Submission fully processed for %s %s <%s>", lead.firstName, lead.lastName, lead.email)

    except Exception as exc:
        logger.exception(
            "Background processing failed for %s %s <%s>: %s",
            lead.firstName,
            lead.lastName,
            lead.email,
            exc,
        )


# ─── Endpoint ────────────────────────────────────────────────────────────────

@app.post("/api/lead/submit-summary")
async def submit_summary(payload: SubmitRequest, background_tasks: BackgroundTasks):
    """
    Validates payload, then offloads heavy work (sheets + email)
    to a background task and immediately returns { ok: true }.
    """
    background_tasks.add_task(_process_submission, payload)
    return {"ok": True}


# ─── PDF tracked download ────────────────────────────────────────────────────

@app.get("/api/pdf/{token}")
def download_pdf(token: str):
    """
    Regenerate and serve the lead's PDF on-demand using data stored in Google
    Sheets.  On first access, records the current timestamp in 'PDF Opened At'
    (col O).  No disk storage required — safe for ephemeral environments.
    """
    if not re.fullmatch(r"[0-9a-f-]{36}", token):
        raise HTTPException(status_code=400, detail="Invalid token")

    # Look up row data from Google Sheets by token
    try:
        row = google_sheets.get_row_by_token(token)
    except Exception:
        logger.exception("Failed to look up token %s in Sheets", token)
        raise HTTPException(status_code=500, detail="Could not retrieve report data")

    if row is None:
        raise HTTPException(status_code=404, detail="Report not found or link has expired")

    # Reconstruct the lead object from stored data
    lead_name: str = row["lead_name"]
    first, _, rest = lead_name.partition(" ")
    lead = SimpleNamespace(
        firstName=first,
        lastName=rest,
        email=row["lead_email"],
        company=row["lead_company"],
        expansionStage=row["expansion_stage"],
    )

    # Recompute scores from stored checklist answers
    scores = scoring.compute_scores(row["checklist_dict"])

    # Generate PDF bytes fresh (no disk I/O needed)
    try:
        pdf_bytes = pdf_service.generate_pdf(lead=lead, scores=scores)
    except Exception:
        logger.exception("PDF generation failed for token %s", token)
        raise HTTPException(status_code=500, detail="Could not generate report")

    # Record first-open timestamp in Google Sheets (best-effort)
    try:
        google_sheets.update_pdf_opened_at(row["row_number"])
    except Exception:
        logger.exception("Failed to update PDF Opened At for token %s", token)

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=India_HR_Readiness_Report.pdf"},
    )


# ─── Global validation error handler ────────────────────────────────────────

@app.exception_handler(422)
async def validation_exception_handler(request: Request, exc):
    logger.error("Validation error on %s %s: %s", request.method, request.url.path, exc.errors())
    return JSONResponse(status_code=422, content={"ok": False, "detail": exc.errors()})


# ─── Health check ────────────────────────────────────────────────────────────

@app.get("/")
@app.get("/health")
def health():
    return {"status": "ok"}

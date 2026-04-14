"""
Google Sheets service — appends one row per lead submission.
Auth: service account JSON via env var or credentials file.
"""
import json
import os
import logging
from datetime import datetime, timezone, timedelta
from typing import List, Any

logger = logging.getLogger(__name__)

SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]


def _get_credentials():
    """Build service account credentials from env."""
    from google.oauth2.service_account import Credentials

    sa_json = os.getenv("GOOGLE_SERVICE_ACCOUNT_JSON")
    if sa_json:
        info = json.loads(sa_json)
        return Credentials.from_service_account_info(info, scopes=SCOPES)

    creds_file = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    if creds_file:
        return Credentials.from_service_account_file(creds_file, scopes=SCOPES)

    raise RuntimeError(
        "No Google credentials found. Set GOOGLE_SERVICE_ACCOUNT_JSON or "
        "GOOGLE_APPLICATION_CREDENTIALS."
    )


def append_lead_row(
    lead_name: str,
    lead_email: str,
    lead_company: str,
    expansion_stage: str,
    overall_score: int,
    section1: int,
    section2: int,
    section3: int,
    section4: int,
    section5: int,
    risk_areas: List[str],
    checklist_dict: dict,
    pdf_token: str = "",
    section_timings: dict = None,
) -> None:
    """Append a single row to the configured Google Sheet."""
    import httplib2
    import google_auth_httplib2
    import googleapiclient.discovery as discovery

    sheet_id = os.environ["GOOGLE_SHEETS_ID"]
    tab_name = os.getenv("GOOGLE_SHEETS_TAB_NAME", "leads")

    creds = _get_credentials()
    http = google_auth_httplib2.AuthorizedHttp(creds, http=httplib2.Http(timeout=30))
    service = discovery.build("sheets", "v4", http=http, cache_discovery=False)

    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    def fmt(ms: int) -> str:
        secs = ms // 1000
        if secs < 60:
            return f"{secs}s"
        m, s = divmod(secs, 60)
        return f"{m}m {s}s" if s else f"{m}m"

    timings = section_timings or {}
    s1 = timings.get("section1", 0)
    s2 = timings.get("section2", 0)
    s3 = timings.get("section3", 0)
    s4 = timings.get("section4", 0)
    s5 = timings.get("section5", 0)
    avg = s1 + s2 + s3 + s4 + s5

    row: List[Any] = [
        timestamp,
        lead_name,
        lead_email,
        lead_company,
        expansion_stage,
        overall_score,
        section1,
        section2,
        section3,
        section4,
        section5,
        json.dumps(risk_areas),
        json.dumps(checklist_dict),
        pdf_token,  # col N — used to find this row when PDF is opened
        "",         # col O — PDF Opened At (filled later by /api/pdf/{token})
        fmt(s1),    # col P — S1
        fmt(s2),    # col Q — S2
        fmt(s3),    # col R — S3
        fmt(s4),    # col S — S4
        fmt(s5),    # col T — S5
        fmt(avg),   # col U — Avg (total)
    ]

    body = {"values": [row]}
    range_notation = f"{tab_name}!A:U"

    service.spreadsheets().values().append(
        spreadsheetId=sheet_id,
        range=range_notation,
        valueInputOption="RAW",
        insertDataOption="INSERT_ROWS",
        body=body,
    ).execute()

    logger.info("Google Sheets row appended for %s <%s>", lead_name, lead_email)


def get_row_by_token(pdf_token: str) -> dict | None:
    """
    Find the row whose column N matches pdf_token and return the data needed
    to regenerate the PDF.  Returns None if the token is not found.

    Returned dict keys: lead_name, lead_email, lead_company,
                        expansion_stage, checklist_dict, row_number
    """
    import httplib2
    import google_auth_httplib2
    import googleapiclient.discovery as discovery

    sheet_id = os.environ["GOOGLE_SHEETS_ID"]
    tab_name = os.getenv("GOOGLE_SHEETS_TAB_NAME", "leads")

    creds = _get_credentials()
    http = google_auth_httplib2.AuthorizedHttp(creds, http=httplib2.Http(timeout=30))
    service = discovery.build("sheets", "v4", http=http, cache_discovery=False)

    # Locate the token in column N
    token_col = service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=f"{tab_name}!N:N",
    ).execute()
    values = token_col.get("values", [])

    row_number = None
    for i, cell in enumerate(values):
        if cell and cell[0] == pdf_token:
            row_number = i + 1  # 1-indexed
            break

    if row_number is None:
        return None

    # Fetch the full row
    row_data = service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=f"{tab_name}!A{row_number}:O{row_number}",
    ).execute()
    row = (row_data.get("values") or [[]])[0]

    # Pad to at least 13 columns so index access is safe
    while len(row) < 13:
        row.append("")

    return {
        "lead_name": row[1],        # col B
        "lead_email": row[2],       # col C
        "lead_company": row[3],     # col D
        "expansion_stage": row[4],  # col E
        "checklist_dict": json.loads(row[12]) if row[12] else {},  # col M
        "row_number": row_number,
    }


def update_pdf_opened_at(row_number: int) -> None:
    """
    Write the current IST timestamp into column O (PDF Opened At) for the
    given 1-indexed row.  Only records the first open; skips if already set.
    """
    import httplib2
    import google_auth_httplib2
    import googleapiclient.discovery as discovery

    sheet_id = os.environ["GOOGLE_SHEETS_ID"]
    tab_name = os.getenv("GOOGLE_SHEETS_TAB_NAME", "leads")

    creds = _get_credentials()
    http = google_auth_httplib2.AuthorizedHttp(creds, http=httplib2.Http(timeout=30))
    service = discovery.build("sheets", "v4", http=http, cache_discovery=False)

    # Only record the first open
    existing = service.spreadsheets().values().get(
        spreadsheetId=sheet_id,
        range=f"{tab_name}!O{row_number}",
    ).execute()
    if existing.get("values"):
        logger.info("PDF already marked as opened for row %d — skipping", row_number)
        return

    IST = timezone(timedelta(hours=5, minutes=30))
    timestamp = datetime.now(IST).strftime("%Y-%m-%d %H:%M:%S IST")
    service.spreadsheets().values().update(
        spreadsheetId=sheet_id,
        range=f"{tab_name}!O{row_number}",
        valueInputOption="RAW",
        body={"values": [[timestamp]]},
    ).execute()

    logger.info("PDF Opened At set to %s (row %d)", timestamp, row_number)

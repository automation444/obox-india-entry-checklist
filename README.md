# India HR Readiness Assessment — FastAPI Backend

FastAPI backend for the India HR Readiness Assessment wizard.  
**On every lead submission it:**
1. Validates the 20-question checklist + lead details
2. Computes readiness scores (overall + 5 sections + risk areas)
3. Appends a row to Google Sheets
4. Generates a personalized PDF report (Jinja2 → WeasyPrint)
5. Emails the PDF to the submitting lead

All heavy work runs in a **BackgroundTask** so the API returns `{ "ok": true }` instantly.

---

## Project structure

```
app/
  main.py                  # FastAPI app + endpoint
  models.py                # Pydantic request models + validation
  services/
    scoring.py             # Readiness scoring engine (ports frontend logic)
    google_sheets.py       # Append row to Google Sheets
    pdf_service.py         # Jinja2 render → WeasyPrint → PDF bytes
    email_service.py       # SMTP email with PDF attachment
  templates/
    readiness_report.html  # Jinja2 HTML template for the PDF
    report.css             # PDF styles (WeasyPrint reads this)
  assets/
    OboxLogo.png           # ← place your logo here
requirements.txt
.env.example
README.md
```

---

## Setup

### 1 — Prerequisites

- Python 3.11+
- WeasyPrint system dependencies  
  - **Ubuntu/Debian:** `sudo apt-get install libpango-1.0-0 libpangoft2-1.0-0 libcairo2`
  - **macOS (Homebrew):** `brew install pango cairo`
  - **Windows:** follow the [WeasyPrint install guide](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html)

### 2 — Install Python dependencies

```bash
cd india-hr-backend
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

### 3 — Configure environment

```bash
cp .env.example .env
# Edit .env and fill in all values
```

**Required env vars:**

| Variable | Description |
|---|---|
| `FRONTEND_ORIGIN` | React dev server URL, e.g. `http://localhost:5173` |
| `GOOGLE_SHEETS_ID` | ID from your Sheet URL |
| `GOOGLE_SHEETS_TAB_NAME` | Tab/sheet name (default: `leads`) |
| `GOOGLE_SERVICE_ACCOUNT_JSON` | Full service account JSON as one-line string |
| `SMTP_HOST` | SMTP server (e.g. `smtp.gmail.com`) |
| `SMTP_PORT` | `587` for TLS, `465` for SSL |
| `SMTP_USER` | Your Gmail address |
| `SMTP_PASSWORD` | Gmail **App Password** (not your regular password) |
| `EMAIL_FROM` | `pawarlaxmi2610@gmail.com` (fixed sender) |

### 4 — Google Sheets setup

1. Create a Google Sheet with a tab named `leads` (or match `GOOGLE_SHEETS_TAB_NAME`)
2. Add this header row in row 1:  
   `timestamp | name | email | company | expansionStage | overallScore | section1 | section2 | section3 | section4 | section5 | riskAreas | readinessChecklist`
3. Create a **service account** in Google Cloud Console → IAM → Service Accounts
4. Download the JSON key
5. Share your Google Sheet with the service account email (`...@....iam.gserviceaccount.com`) as **Editor**
6. Paste the JSON (all on one line) into `GOOGLE_SERVICE_ACCOUNT_JSON`

### 5 — Gmail App Password (for SMTP)

1. Enable 2FA on the Gmail account
2. Go to `myaccount.google.com` → Security → App Passwords
3. Create an app password for "Mail"
4. Use that 16-character password as `SMTP_PASSWORD`

### 6 — Logo

Place your `OboxLogo.png` file in `app/assets/OboxLogo.png`.  
The PDF renders gracefully with a text fallback if the file is missing.

---

## Run

```bash
uvicorn app.main:app --reload
```

API will be available at `http://localhost:8000`.

---

## Test with curl

```bash
curl -s -X POST http://localhost:8000/api/lead/submit-summary \
  -H "Content-Type: application/json" \
  -d '{
  "assessmentData": {
    "readinessChecklist": {
      "q1": "fully_in_place",
      "q2": "partially_in_place",
      "q3": "not_sure_na",
      "q4": "shared_responsibility",
      "q5": "not_started",
      "q6": "fully_in_place",
      "q7": "somewhat_defined",
      "q8": "fully_in_place",
      "q9": "need_advisory",
      "q10": "partially_in_place",
      "q11": "not_sure",
      "q12": "under_discussion",
      "q13": "evaluating_options",
      "q14": "fully_in_place",
      "q15": "partially_in_place",
      "q16": "not_started",
      "q17": "fully_in_place",
      "q18": "already_using",
      "q19": "partially_in_place_q19",
      "q20": "low_confidence"
    }
  },
  "leadData": {
    "name": "Test Lead",
    "email": "your-test-email@gmail.com",
    "company": "Acme Corp Pvt Ltd",
    "expansionStage": "Exploring India entry"
  }
}'
```

Expected response:
```json
{"ok": true}
```

### Verify

| Check | Where |
|---|---|
| Row added | Open your Google Sheet — new row should appear in seconds |
| PDF emailed | Check inbox of `leadData.email` |
| Sender | Email should show `OBOX HR <pawarlaxmi2610@gmail.com>` |
| PDF content | Name, company, scores, risk areas — all personalized |

---

## Health check

```bash
curl http://localhost:8000/health
# {"status":"ok"}
```

## API docs (Swagger UI)

```
http://localhost:8000/docs
```

---

## Scoring logic

| Section | Questions | Label |
|---|---|---|
| Section 1 | q1–q4 | Governance & Entity |
| Section 2 | q5–q8 | Hiring & Documentation |
| Section 3 | q9–q12 | Payroll & Benefits |
| Section 4 | q13–q16 | HR Operations |
| Section 5 | q17–q20 | Scale & Risk |

**Section % formula:** `round((sectionPoints / 20) * 100)`  
**Overall score:** average of 5 section percentages  
**Risk areas:** questions where answer score == 0  
**Weak sections:** sections where percent < 60  

**Status thresholds:**
- ≥ 80 → Strong foundation (green)
- 55–79 → Partially ready (yellow)
- < 55 → Critical gaps (red)

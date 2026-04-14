"""
Scoring logic mirroring PLAYBOOK_PHASES in obox-shared.js.

overall = sum of all 20 raw question scores (each 0–5, max 100) — matches frontend.
section % = round((sectionPoints / 20) * 100)
"""
from dataclasses import dataclass, field
from typing import Dict, List

# Per-question score maps — mirrors obox-shared.js PHASES option values exactly
PER_QUESTION_SCORES: Dict[str, Dict[str, int]] = {
    # Section 1 — Statutory Compliance & Governance
    "c1": {"fully": 5, "partially": 3, "notstarted": 0, "notsure": 1},
    "c2": {"fully": 5, "partially": 3, "notstarted": 0, "notsure": 1},
    "c3": {"fully": 5, "partially": 3, "notstarted": 0, "notsure": 1},
    "c4": {"internal": 5, "external": 4, "shared": 2, "noowner": 0},
    # Section 2 — Hiring & Employment Documentation
    "h1": {"fully": 5, "partially": 3, "notstarted": 0, "notsure": 1},
    "h2": {"fully": 5, "partially": 3, "notstarted": 0, "notsure": 1},
    "h3": {"fully": 5, "partially": 3, "evaluating": 1, "notstarted": 0},
    "h4": {"fully": 5, "partially": 3, "notstarted": 0, "notsure": 1},
    # Section 3 — Payroll, Tax & Control Environment
    "p1": {"fully": 5, "partially": 3, "notstarted": 0, "needadvisory": 1},
    "p2": {"fully": 5, "partially": 3, "notstarted": 0, "notsure": 1},
    "p3": {"fully": 5, "partially": 3, "notstarted": 0, "notsure": 1},
    "p4": {"fully": 5, "partially": 3, "notstarted": 0, "needsupport": 1},
    # Section 4 — HR Operations & Employee Experience
    "o1": {"fully": 5, "evaluating": 3, "notstarted": 0, "manual": 1},
    "o2": {"fully": 5, "partially": 3, "notstarted": 0, "notsure": 1},
    "o3": {"fully": 5, "partially": 3, "notstarted": 0, "notsure": 1},
    "o4": {"fully": 5, "partially": 3, "notstarted": 0, "notsure": 1},
    # Section 5 — Scale, Risk & Ongoing Support
    "s1": {"fully": 5, "partially": 3, "notstarted": 0, "notsure": 1},
    "s2": {"fully": 5, "evaluating": 3, "notstarted": 1, "notneeded": 4},
    "s3": {"fully": 5, "partially": 3, "notstarted": 0, "notapplicable": 4},
    "s4": {"fully": 5, "partially": 3, "notstarted": 1, "notsure": 0},
}

# Human-readable labels for each question (used in risk_areas list)
QUESTION_LABELS: Dict[str, str] = {
    "c1": "Labour Law Registrations Identified",
    "c2": "Statutory Registrations (PF / ESIC / PT)",
    "c3": "POSH Compliance",
    "c4": "Compliance Ownership",
    "h1": "Employment Documents & Agreements",
    "h2": "Employee Handbook & Policies",
    "h3": "Hiring Model Clarity",
    "h4": "Background Verification & Onboarding",
    "p1": "Tax-Friendly Compensation Structure",
    "p2": "Payroll Processing Model",
    "p3": "Payslips, TDS & Form 16 Processes",
    "p4": "Employee Benefits Decision",
    "o1": "HRMS / HR System",
    "o2": "Employee Records & HR Workflows",
    "o3": "HR & Payroll Query Support Model",
    "o4": "Employee Lifecycle Process",
    "s1": "Ongoing Payroll & Compliance Plan",
    "s2": "Outsourced HR / Virtual HR Manager",
    "s3": "Operational & Advisory Support",
    "s4": "12-Month Scale Confidence",
}

# Section definitions — matches PLAYBOOK_PHASES order
SECTION_QUESTIONS = {
    1: ["c1", "c2", "c3", "c4"],
    2: ["h1", "h2", "h3", "h4"],
    3: ["p1", "p2", "p3", "p4"],
    4: ["o1", "o2", "o3", "o4"],
    5: ["s1", "s2", "s3", "s4"],
}

# Labels match frontend SECTION_DISPLAY_LABELS
SECTION_LABELS = {
    1: "Governance",
    2: "Hiring & Documentation",
    3: "Payroll & Benefits",
    4: "HR Operations",
    5: "Scale & Risk",
}

MAX_POINTS_PER_SECTION = 20  # 4 questions × 5 points each


@dataclass
class SectionResult:
    label: str
    percent: int
    color_class: str


@dataclass
class ScoreResult:
    overall: int
    status_text: str
    status_class: str
    sections: List[SectionResult]
    weak_sections: List[str]
    risk_areas: List[str]
    # raw section percentages stored for Google Sheets row
    section1_percent: int = 0
    section2_percent: int = 0
    section3_percent: int = 0
    section4_percent: int = 0
    section5_percent: int = 0


def _section_color(percent: int) -> str:
    if percent >= 70:
        return "bar-success"
    elif percent >= 40:
        return "bar-warning"
    return "bar-danger"


def _overall_status(score: int):
    if score >= 80:
        return "Strong foundation in place", "status-success"
    elif score >= 55:
        return "Partially ready — gaps exist", "status-warning"
    return "Critical gaps — immediate action needed", "status-danger"


def compute_scores(checklist: Dict[str, str]) -> ScoreResult:
    """
    checklist: dict of c1..s4 -> answer value
    Returns ScoreResult with all analytics.

    overall = sum of all raw q scores (0–5 each, max 100) — mirrors frontend totalRaw.
    """
    # Per-question raw scores
    q_scores = {
        q: PER_QUESTION_SCORES.get(q, {}).get(ans, 0)
        for q, ans in checklist.items()
    }

    # Risk areas: questions where score == 0
    risk_areas = [
        QUESTION_LABELS[q]
        for q in sorted(q_scores.keys())
        if q_scores[q] == 0 and q in QUESTION_LABELS
    ]

    # Section percentages
    section_percents: Dict[int, int] = {}
    for sec_num, qs in SECTION_QUESTIONS.items():
        pts = sum(q_scores.get(q, 0) for q in qs)
        pct = round((pts / MAX_POINTS_PER_SECTION) * 100)
        section_percents[sec_num] = pct

    # Overall = sum of all raw scores (matches frontend totalRaw, max=100)
    overall = sum(q_scores.values())

    # Weak sections (section % < 60)
    weak_sections = [
        SECTION_LABELS[sec_num]
        for sec_num, pct in section_percents.items()
        if pct < 60
    ]

    status_text, status_class = _overall_status(overall)

    sections = [
        SectionResult(
            label=SECTION_LABELS[i],
            percent=section_percents[i],
            color_class=_section_color(section_percents[i]),
        )
        for i in range(1, 6)
    ]

    return ScoreResult(
        overall=overall,
        status_text=status_text,
        status_class=status_class,
        sections=sections,
        weak_sections=weak_sections,
        risk_areas=risk_areas,
        section1_percent=section_percents[1],
        section2_percent=section_percents[2],
        section3_percent=section_percents[3],
        section4_percent=section_percents[4],
        section5_percent=section_percents[5],
    )

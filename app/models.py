from pydantic import BaseModel, EmailStr, field_validator, model_validator

VALID_Q_ANSWERS = {
    # Section 1 — Statutory Compliance & Governance
    "c1": ["fully", "partially", "notstarted", "notsure"],
    "c2": ["fully", "partially", "notstarted", "notsure"],
    "c3": ["fully", "partially", "notstarted", "notsure"],
    "c4": ["internal", "external", "shared", "noowner"],
    # Section 2 — Hiring & Employment Documentation
    "h1": ["fully", "partially", "notstarted", "notsure"],
    "h2": ["fully", "partially", "notstarted", "notsure"],
    "h3": ["fully", "partially", "evaluating", "notstarted"],
    "h4": ["fully", "partially", "notstarted", "notsure"],
    # Section 3 — Payroll, Tax & Control Environment
    "p1": ["fully", "partially", "notstarted", "needadvisory"],
    "p2": ["fully", "partially", "notstarted", "notsure"],
    "p3": ["fully", "partially", "notstarted", "notsure"],
    "p4": ["fully", "partially", "notstarted", "needsupport"],
    # Section 4 — HR Operations & Employee Experience
    "o1": ["fully", "evaluating", "notstarted", "manual"],
    "o2": ["fully", "partially", "notstarted", "notsure"],
    "o3": ["fully", "partially", "notstarted", "notsure"],
    "o4": ["fully", "partially", "notstarted", "notsure"],
    # Section 5 — Scale, Risk & Ongoing Support
    "s1": ["fully", "partially", "notstarted", "notsure"],
    "s2": ["fully", "evaluating", "notstarted", "notneeded"],
    "s3": ["fully", "partially", "notstarted", "notapplicable"],
    "s4": ["fully", "partially", "notstarted", "notsure"],
}

EXPANSION_STAGES = [
    "Exploring India entry",
    "Setting up entity / operations",
    "Hiring first employees",
    "Scaling existing team",
    "Reviewing current setup",
]


class ReadinessChecklist(BaseModel):
    c1: str
    c2: str
    c3: str
    c4: str
    h1: str
    h2: str
    h3: str
    h4: str
    p1: str
    p2: str
    p3: str
    p4: str
    o1: str
    o2: str
    o3: str
    o4: str
    s1: str
    s2: str
    s3: str
    s4: str

    @model_validator(mode="after")
    def validate_all_answers(self):
        for qkey, valid in VALID_Q_ANSWERS.items():
            val = getattr(self, qkey)
            if val not in valid:
                raise ValueError(
                    f"Invalid answer '{val}' for {qkey}. Valid options: {valid}"
                )
        return self


class AssessmentData(BaseModel):
    readinessChecklist: ReadinessChecklist
    sectionTimings: dict[str, int] = {}


class LeadData(BaseModel):
    firstName: str
    lastName: str
    email: EmailStr
    company: str
    expansionStage: str

    @field_validator("firstName", "lastName", "company")
    @classmethod
    def not_empty(cls, v):
        if not v or not v.strip():
            raise ValueError("Field cannot be empty")
        return v.strip()

    @field_validator("expansionStage")
    @classmethod
    def valid_stage(cls, v):
        if v not in EXPANSION_STAGES:
            raise ValueError(f"expansionStage must be one of: {EXPANSION_STAGES}")
        return v


class SubmitRequest(BaseModel):
    assessmentData: AssessmentData
    leadData: LeadData
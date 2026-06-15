"""A2A workflow step definitions.

The wizard is config-driven: each Step declares a `condition(answers)` that
decides whether it appears. `active_steps(answers)` recomputes the live list on
every request, so answers on one step can add or remove later steps.
"""
from dataclasses import dataclass, field
from typing import Callable


@dataclass
class Step:
    id: str
    title: str
    fields: list = field(default_factory=list)
    condition: Callable = lambda answers: True
    intro: str = ""


PURPOSE_CHOICES = ["New Position", "Replacement", "Extension", "Consultancy"]
DECISION_CHOICES = ["Approve", "Reject", "Refer back"]

DEPARTMENTS = [
    "",
    "Clinical Sciences",
    "External Relations",
    "Education",
    "Enterprise and Innovation",
    "Estates",
    "Financial Services",
    "Human Resources",
    "Health and Safety",
    "Legal and Governance",
    "International Public Health",
    "IT Services",
    "Vice-Chancellor's Office",
    "Research Services",
    "Research and Education Facilities",
    "Strategic Planning",
    "COO's Office",
    "Tropical Disease Biology",
    "Vector Biology",
]


def approval_fields(prefix: str) -> list:
    """Standard field set for an approval step."""
    return [
        {"name": f"{prefix}_name", "label": "Approver name", "type": "text"},
        {"name": f"{prefix}_decision", "label": "Decision", "type": "radio",
         "options": DECISION_CHOICES},
        {"name": f"{prefix}_comments", "label": "Comments", "type": "textarea"},
    ]


def funding_active(n: int) -> Callable:
    """Source of Funding 1 always shows; 2-5 appear only if the previous step
    ticked 'add another source of funding'. Finance Approval n reuses this."""
    def cond(answers):
        if n == 1:
            return True
        return answers.get(f"add_funding_{n}") == "on"
    return cond


# ---------------------------------------------------------------------------
# Step list (order matters)
# ---------------------------------------------------------------------------
STEPS: list = []

# 1. Purpose — opening page; drives which sub-step appears
STEPS.append(Step(
    "purpose", "A2A Purpose",
    fields=[
        {"name": "current_user", "label": "Current User", "type": "user",
         "required": True, "disabled": True, "default": "Daniel Williams"},
        {"name": "purpose", "label": "A2A purpose", "type": "select",
         "options": PURPOSE_CHOICES, "required": True,
         "help": "Choose the request type. See the guidance above for what each "
                 "option covers."},
        {"name": "department", "label": "Department", "type": "select",
         "options": DEPARTMENTS, "required": True,
         "help": "Select the department this request relates to."},
        {"name": "departmental_group", "label": "Departmental Group",
         "type": "text", "required": True},
        {"name": "line_manager", "label": "Line Manager", "type": "user",
         "required": True, "placeholder": "Enter user names, email addresses…",
         "validate": "entra_user",
         "help": "Start typing a name or email and pick the line manager from "
                 "the directory. Must be a valid user in the tenant."},
    ],
))

# 2. Purpose-specific sub-steps (only the chosen one shows)
STEPS.append(Step(
    "extension", "Extension",
    condition=lambda a: a.get("purpose") == "Extension",
    fields=[
        {"name": "extension_post", "label": "Post being extended", "type": "text"},
        {"name": "extension_reason", "label": "Reason for extension", "type": "textarea"},
        {"name": "extension_end_date", "label": "New end date", "type": "date"},
    ],
))
STEPS.append(Step(
    "new_position", "New Position",
    condition=lambda a: a.get("purpose") == "New Position",
    fields=[
        {"name": "new_title", "label": "Job title", "type": "text"},
        {"name": "new_grade", "label": "Grade", "type": "text"},
        {"name": "new_justification", "label": "Justification", "type": "textarea"},
    ],
))
STEPS.append(Step(
    "replacement", "Replacement",
    condition=lambda a: a.get("purpose") == "Replacement",
    fields=[
        {"name": "replacement_leaver", "label": "Person being replaced", "type": "text"},
        {"name": "replacement_title", "label": "Job title", "type": "text"},
        {"name": "replacement_changes", "label": "Any changes to the role?", "type": "textarea"},
    ],
))
STEPS.append(Step(
    "consultancy", "Consultancy",
    condition=lambda a: a.get("purpose") == "Consultancy",
    fields=[
        {"name": "consultancy_supplier", "label": "Consultant / supplier", "type": "text"},
        {"name": "consultancy_scope", "label": "Scope of work", "type": "textarea"},
        {"name": "consultancy_value", "label": "Estimated value (£)", "type": "number"},
    ],
))

# 3. Sources of Funding 1-5 (each can spawn the next)
for n in range(1, 6):
    f = [
        {"name": f"funding_source_{n}", "label": f"Funding source {n} name", "type": "text"},
        {"name": f"funding_code_{n}", "label": "Cost centre / code", "type": "text"},
        {"name": f"funding_pct_{n}", "label": "% of total funding", "type": "number"},
    ]
    if n < 5:
        f.append({"name": f"add_funding_{n + 1}",
                  "label": "Add another source of funding?", "type": "checkbox"})
    STEPS.append(Step(f"funding_{n}", f"Source of Funding {n}",
                      fields=f, condition=funding_active(n)))

# 4. Approval chain
STEPS.append(Step("line_approval", "Line Approval Manager",
                  fields=approval_fields("line")))
STEPS.append(Step("director_approval", "Director/Head of Department Approval",
                  fields=approval_fields("director")))

# Finance Approval 1-5 — one per active funding source
for n in range(1, 6):
    STEPS.append(Step(f"finance_approval_{n}", f"Finance Approval {n}",
                      fields=approval_fields(f"finance_{n}"),
                      condition=funding_active(n)))

STEPS.append(Step("head_mgmt_accounting", "Head of Management Accounting Approval",
                  fields=approval_fields("head_mgmt")))
STEPS.append(Step("head_rms", "Head of RMS Approval",
                  fields=approval_fields("head_rms")))
STEPS.append(Step("hr_signoff", "HR Sign-off",
                  fields=approval_fields("hr_signoff")))
STEPS.append(Step("hr_processing", "HR Processing",
                  fields=[
                      {"name": "hr_ref", "label": "HR reference number", "type": "text"},
                      {"name": "hr_notes", "label": "Processing notes", "type": "textarea"},
                  ]))


# ---------------------------------------------------------------------------
# Engine helpers
# ---------------------------------------------------------------------------
def active_steps(answers: dict) -> list:
    return [s for s in STEPS if s.condition(answers)]


def get_step(step_id: str):
    return next((s for s in STEPS if s.id == step_id), None)


def index_of(active: list, step_id: str):
    for i, s in enumerate(active):
        if s.id == step_id:
            return i
    return None

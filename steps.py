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

# Departmental Group is derived from the chosen Department (read-only on the form).
DEPARTMENT_GROUPS = {
    "Biological Sciences": [
        "Tropical Disease Biology", "Vector Biology"],
    "Clinical Sciences and International Public Health": [
        "Clinical Sciences", "International Public Health"],
    "COO's Office": [
        "COO's Office", "Estates", "Financial Services", "Research Services",
        "IT Services", "Enterprise and Innovation", "Strategic Planning",
        "Legal and Governance", "Health and Safety"],
    "Professional Services": [
        "External Relations", "Vice-Chancellor's Office", "Human Resources",
        "Research and Education Facilities"],
    "Education": ["Education"],
}
# Flattened department -> group lookup.
DEPARTMENT_TO_GROUP = {
    dept: group
    for group, depts in DEPARTMENT_GROUPS.items()
    for dept in depts
}


def group_for(department: str) -> str:
    """Return the Departmental Group for a department ('' if unknown)."""
    return DEPARTMENT_TO_GROUP.get(department, "")


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
POSITION_TYPES = ["Staff", "Agency", "Work Placement"]
PAYSCALES = [
    "HERA (Grades 1-9)",
    "HERA (Grades 1-9, Malawi)",
    "Clinical Academic (doctors in training)",
    "Clinical Academic (Clinical Lecturer)",
    "Clinical Academic (Senior Lecturer/Reader)",
    "Clinical Academic (Consultant)",
    "NHS (Agenda for Change)",
    "Professorial/Corporate Leader",
    "Offscale",
]
POSITION_CLASSIFICATIONS = [
    "Teaching Only", "Research Only", "Teaching & Research", "Other"]
CONTRACT_BASES = ["Full-time (35 hours per week)", "Part-time"]
YES_NO = ["Yes", "No"]
WORK_PATTERN_DAYS = [
    ("mon", "Monday"), ("tue", "Tuesday"), ("wed", "Wednesday"),
    ("thu", "Thursday"), ("fri", "Friday"), ("sat", "Saturday"),
    ("sun", "Sunday"),
]

_new_position_fields = [
    # --- Position Details ---
    {"name": "np_position_type", "label": "Position Type", "type": "select",
     "options": POSITION_TYPES, "required": True, "section": "Position Details"},
    {"name": "np_job_title", "label": "Job Title", "type": "text",
     "required": True, "section": "Position Details"},
    # Department & Line Manager are display-only (carried from the Purpose page).
    {"name": "np_location", "label": "Position Location", "type": "text",
     "required": True, "section": "Position Details",
     "help": "Where the role will be based."},
    {"name": "np_payscale", "label": "Payscale", "type": "select",
     "options": PAYSCALES, "required": True, "section": "Position Details",
     "help": "Select the applicable payscale for this position."},
    {"name": "np_grade", "label": "Grade", "type": "text", "required": True,
     "section": "Position Details", "help": "Enter the grade for this position."},
    {"name": "np_spinal_point", "label": "Spinal Point", "type": "text",
     "required": True, "section": "Position Details",
     "help": "Enter the spinal point for this position."},
    {"name": "np_classification", "label": "Position classification",
     "type": "select", "options": POSITION_CLASSIFICATIONS, "required": True,
     "section": "Position Details",
     "help": "Select the classification that applies to this position."},
    {"name": "np_classification_code", "label": "Position classification code",
     "type": "text", "required": True, "section": "Position Details"},
    {"name": "np_contract_basis", "label": "Contract Basis", "type": "select",
     "options": CONTRACT_BASES, "required": True, "section": "Position Details"},
    # Working pattern (np_hours_<day>) is rendered as a grid in the template.
    {"name": "np_start_date", "label": "Estimated position start-date",
     "type": "date", "required": True, "section": "Position Details"},
    {"name": "np_child_contact",
     "label": "Will this role have direct or indirect contact with children "
              "and/or vulnerable adults?",
     "type": "radio", "options": YES_NO, "required": True,
     "section": "Position Details"},
    {"name": "np_justification", "label": "Justification for new position",
     "type": "textarea", "required": True, "section": "Position Details",
     "help": "Explain why this new position is needed."},
    # --- Recruitment Information ---
    {"name": "np_recruit_budget",
     "label": "Is there a budget available for recruitment purposes?",
     "type": "radio", "options": YES_NO, "required": True,
     "section": "Recruitment Information"},
    {"name": "np_advert_cost_centre",
     "label": "What cost centre should the advertising be charged to?",
     "type": "text", "section": "Recruitment Information"},
    {"name": "np_advert_sources", "label": "Suggested sources for advertisement",
     "type": "textarea", "section": "Recruitment Information"},
]
# Working-pattern hours, one number field per day (Mon-Sun).
_new_position_fields += [
    {"name": f"np_hours_{key}", "label": label, "type": "number",
     "section": "Position Details", "widget": "workpattern"}
    for key, label in WORK_PATTERN_DAYS
]

STEPS.append(Step(
    "new_position", "New Position",
    condition=lambda a: a.get("purpose") == "New Position",
    fields=_new_position_fields,
))
REPLACEMENT_TYPES = ["Staff", "Agency"]

_replacement_fields = [
    {"name": "rp_replacement_type", "label": "Replacement type", "type": "select",
     "options": REPLACEMENT_TYPES, "required": True, "section": "_top"},
    {"name": "rp_name_replaced", "label": "Name of person being replaced",
     "type": "text", "required": True, "section": "_top"},
    # --- Position Details ---
    {"name": "rp_job_title", "label": "Job Title", "type": "text",
     "required": True, "section": "Position Details"},
    # Department & Line Manager are display-only (carried from the Purpose page).
    {"name": "rp_start_date", "label": "Estimated start-date of replacement",
     "type": "date", "required": True, "section": "Position Details"},
    {"name": "rp_payscale", "label": "Payscale", "type": "select",
     "options": PAYSCALES, "required": True, "section": "Position Details",
     "help": "Select the applicable payscale for this position."},
    {"name": "rp_grade", "label": "Grade", "type": "text", "required": True,
     "section": "Position Details", "help": "Enter the grade for this position."},
    {"name": "rp_spinal_point", "label": "Spinal Point", "type": "text",
     "required": True, "section": "Position Details",
     "help": "Enter the spinal point for this position."},
    {"name": "rp_location", "label": "Position Location", "type": "text",
     "required": True, "section": "Position Details",
     "help": "Where the role will be based."},
    {"name": "rp_hours_per_week",
     "label": "Please enter number of hours to be worked per week",
     "type": "number", "required": True, "section": "Position Details"},
    # Working pattern (rp_hours_<day>) is rendered as a grid in the template
    # and is optional ("if known").
    {"name": "rp_classification", "label": "Position Classification",
     "type": "select", "options": POSITION_CLASSIFICATIONS, "required": True,
     "section": "Position Details",
     "help": "Select the classification that applies to this position."},
    {"name": "rp_classification_code", "label": "Position classification code",
     "type": "text", "required": True, "section": "Position Details"},
    {"name": "rp_child_contact",
     "label": "Does this role involve direct or indirect contact with children "
              "and/or vulnerable adults?",
     "type": "radio", "options": YES_NO, "required": True,
     "section": "Position Details"},
    # --- Justification ---
    {"name": "rp_justification", "label": "Justification for Replacement",
     "type": "textarea", "required": True, "section": "Justification"},
    # --- Recruitment Information ---
    {"name": "rp_recruit_budget",
     "label": "Is there a budget available for recruitment purposes?",
     "type": "radio", "options": YES_NO, "required": True,
     "section": "Recruitment Information"},
    {"name": "rp_advert_cost_centre",
     "label": "What cost centre should the advertising be charged to?",
     "type": "text", "section": "Recruitment Information"},
    {"name": "rp_advert_sources", "label": "Suggested sources of advertising",
     "type": "textarea", "section": "Recruitment Information"},
]
# Working-pattern hours, one number field per day (Mon-Sun); optional.
_replacement_fields += [
    {"name": f"rp_hours_{key}", "label": label, "type": "number",
     "section": "Position Details", "widget": "workpattern"}
    for key, label in WORK_PATTERN_DAYS
]

STEPS.append(Step(
    "replacement", "Replacement",
    condition=lambda a: a.get("purpose") == "Replacement",
    fields=_replacement_fields,
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

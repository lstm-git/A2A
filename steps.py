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

# 2. Purpose-specific sub-steps (only the chosen one shows). Extension is built
#    after the shared constants below (it reuses CONTRACT_BASES / WORK_PATTERN_DAYS).
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
# Position classification code is derived from the classification choice.
CLASSIFICATION_CODES = {
    "Teaching Only": "40",
    "Research Only": "41",
    "Teaching & Research": "42",
    "Other": "43",
}


def code_for_classification(value: str) -> str:
    """Return the position classification code ('' if unknown)."""
    return CLASSIFICATION_CODES.get(value, "")
CONTRACT_BASES = ["Full-time (35 hours per week)", "Part-time"]
YES_NO = ["Yes", "No"]
WORK_PATTERN_DAYS = [
    ("mon", "Monday"), ("tue", "Tuesday"), ("wed", "Wednesday"),
    ("thu", "Thursday"), ("fri", "Friday"), ("sat", "Saturday"),
    ("sun", "Sunday"),
]

EXTENSION_PURPOSES = [
    "Conversion of fixed term contract to Permanent",
    "Extension of fixed-term contract",
    "Extension of agency contract",
    "Extension of funding for permanent contract",
    "Change to weekly working hours only (no contract extension)",
]
CONVERSION_PURPOSE = "Conversion of fixed term contract to Permanent"
HOURS_CHANGE_PURPOSE = "Change to weekly working hours only (no contract extension)"
CHANGE_DURATIONS = ["Ongoing", "Temporary"]
# Extension from/to dates apply to every purpose except the hours-only change.
EXTENSION_DATE_PURPOSES = [
    p for p in EXTENSION_PURPOSES if p != HOURS_CHANGE_PURPOSE]

_extension_fields = [
    # Purpose of Request — shown at the top of the form (above Person Details).
    {"name": "ex_request_type", "label": "Purpose of Request", "type": "select",
     "options": EXTENSION_PURPOSES, "required": True, "section": "_top"},
    # --- Person Details ---
    {"name": "ex_employee_name", "label": "Employee/agency worker name",
     "type": "text", "required": True, "section": "Person Details"},
    {"name": "ex_job_title", "label": "Job Title", "type": "text",
     "required": True, "section": "Person Details"},
    # Department & Line Manager are display-only (carried from the Purpose page).
    # --- Details of extension/hours change ---
    # Purpose-driven date questions (all conditional on ex_request_type).
    # Extension from/to: every purpose except the hours-only change.
    {"name": "ex_extension_from", "label": "Extension from", "type": "date",
     "section": "Details of extension/hours change",
     "show_when": ("ex_request_type", EXTENSION_DATE_PURPOSES)},
    {"name": "ex_extension_to", "label": "Extension to", "type": "date",
     "section": "Details of extension/hours change",
     "show_when": ("ex_request_type", EXTENSION_DATE_PURPOSES)},
    # Conversion to permanent only.
    {"name": "ex_current_contract_end",
     "label": "Current fixed-term contract end date", "type": "date",
     "section": "Details of extension/hours change",
     "show_when": ("ex_request_type", [CONVERSION_PURPOSE])},
    # Hours-only change questions.
    {"name": "ex_hours_effective_date",
     "label": "Effective date of change to working hours", "type": "date",
     "section": "Details of extension/hours change",
     "show_when": ("ex_request_type", [HOURS_CHANGE_PURPOSE])},
    {"name": "ex_change_duration",
     "label": "Is this an ongoing or temporary change?", "type": "radio",
     "options": CHANGE_DURATIONS,
     "section": "Details of extension/hours change",
     "show_when": ("ex_request_type", [HOURS_CHANGE_PURPOSE])},
    {"name": "ex_change_details", "label": "Please provide further details",
     "type": "textarea", "section": "Details of extension/hours change",
     "show_when": ("ex_change_duration", "Temporary")},
    {"name": "ex_multiple_positions",
     "label": "Does this person have more than 1 position?", "type": "radio",
     "options": YES_NO, "section": "Details of extension/hours change",
     "show_when": ("ex_request_type", [HOURS_CHANGE_PURPOSE])},
    {"name": "ex_other_positions_detail",
     "label": "Please state whether this hours change will affect the person's "
              "other positions in any way", "type": "textarea",
     "section": "Details of extension/hours change",
     "show_when": ("ex_multiple_positions", "Yes")},
    # Weekly working hours: same Full-time/Part-time mechanism as New Position /
    # Replacement (uniform). Part-time reveals the hours field below.
    {"name": "ex_contract_basis", "label": "Contract Basis", "type": "select",
     "options": CONTRACT_BASES, "required": True,
     "section": "Details of extension/hours change"},
    {"name": "ex_part_time_hours",
     "label": "Please enter number of hours to be worked per week",
     "type": "number", "section": "Details of extension/hours change",
     "show_when": ("ex_contract_basis", "Part-time")},
    # Working pattern (ex_hours_<day>) is rendered as a grid in the template.
    {"name": "ex_grade_change",
     "label": "Please confirm whether any change to the grade for this position",
     "type": "text", "required": True,
     "section": "Details of extension/hours change",
     "help": "State the new grade, or confirm 'No change'."},
    {"name": "ex_spinal_point_change",
     "label": "Please confirm whether any change to the spinal point for this "
              "position",
     "type": "text", "required": True,
     "section": "Details of extension/hours change",
     "help": "State the new spinal point, or confirm 'No change'."},
    {"name": "ex_location",
     "label": "Please confirm person's work location (city/country)",
     "type": "text", "required": True,
     "section": "Details of extension/hours change"},
    # --- Justification ---
    {"name": "ex_justification", "label": "Justification", "type": "textarea",
     "required": True, "section": "Justification"},
]
# Working-pattern hours, one number field per day (Mon-Sun).
_extension_fields += [
    {"name": f"ex_hours_{key}", "label": label, "type": "number",
     "section": "Details of extension/hours change", "widget": "workpattern"}
    for key, label in WORK_PATTERN_DAYS
]

STEPS.append(Step(
    "extension", "Extension",
    condition=lambda a: a.get("purpose") == "Extension",
    fields=_extension_fields,
))

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
    {"name": "np_clinical_duties",
     "label": "Does this role include Clinical Duties?", "type": "radio",
     "options": YES_NO, "section": "Position Details",
     "show_when": ("np_classification", "Other")},
    {"name": "np_contract_basis", "label": "Contract Basis", "type": "select",
     "options": CONTRACT_BASES, "required": True, "section": "Position Details"},
    # Shown only for Part-time; Full-time implies 35 hours (from the option label).
    {"name": "np_part_time_hours",
     "label": "Please enter number of hours to be worked per week",
     "type": "number", "section": "Position Details",
     "show_when": ("np_contract_basis", "Part-time")},
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
    {"name": "np_recruit_budget_amount", "label": "Please enter recruitment budget",
     "type": "number", "section": "Recruitment Information",
     "show_when": ("np_recruit_budget", "Yes")},
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
    {"name": "rp_contract_basis", "label": "Contract Basis", "type": "select",
     "options": CONTRACT_BASES, "required": True, "section": "Position Details"},
    # Shown only for Part-time; Full-time implies 35 hours (from the option label).
    {"name": "rp_part_time_hours",
     "label": "Please enter number of hours to be worked per week",
     "type": "number", "section": "Position Details",
     "show_when": ("rp_contract_basis", "Part-time")},
    # Working pattern (rp_hours_<day>) is rendered as a grid in the template.
    {"name": "rp_classification", "label": "Position Classification",
     "type": "select", "options": POSITION_CLASSIFICATIONS, "required": True,
     "section": "Position Details",
     "help": "Select the classification that applies to this position."},
    {"name": "rp_classification_code", "label": "Position classification code",
     "type": "text", "required": True, "section": "Position Details"},
    {"name": "rp_clinical_duties",
     "label": "Does this role include Clinical Duties?", "type": "radio",
     "options": YES_NO, "section": "Position Details",
     "show_when": ("rp_classification", "Other")},
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
    {"name": "rp_recruit_budget_amount", "label": "Please enter recruitment budget",
     "type": "number", "section": "Recruitment Information",
     "show_when": ("rp_recruit_budget", "Yes")},
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
# Consultancy. NOTE: the option lists below are placeholders pending the real
# values (mirrors how the Department list started). Flagged in the DEVLOG.
CONSULTANCY_APPROVAL_FOR = [
    "New consultancy", "Extension of existing consultancy"]
CONSULTANCY_CONTRACT_TYPES = [
    "Contingent Worker", "UK Consultancy", "Non-UK Consultancy",
    "Contract for Services"]
VAT_STATUS_OPTIONS = [
    "VAT not applicable due to exempt service being provided",
    "Service is subject to VAT but as service is provided overseas there is no "
    "VAT on invoice (but reverse charge VAT will be applied)",
    "Service is subject to VAT and provided in the UK so VAT on invoice"]
PAY_CURRENCIES = ["GBP (£)", "USD ($)", "EUR (€)"]
PAY_FREQUENCIES = [
    "Per hour", "Per day", "Per week", "Per month", "Per annum", "Fixed total"]

_consultancy_fields = [
    {"name": "cy_approval_for", "label": "Approval required for", "type": "select",
     "options": CONSULTANCY_APPROVAL_FOR, "required": True, "section": "_top",
     "help": "Select what this approval request is for."},
    # Department is display-only (carried from the Purpose page).
    {"name": "cy_justification", "label": "Justification for Consultancy",
     "type": "textarea", "required": True, "section": "_top"},
    {"name": "cy_overseer_name", "label": "Assignment Overseer Name",
     "type": "text", "required": True, "section": "_top"},
    {"name": "cy_lstm_manager", "label": "LSTM Manager Name", "type": "text",
     "required": True, "section": "_top"},
    # --- Assignment Details ---
    {"name": "cy_job_title", "label": "Assignment Job Title", "type": "text",
     "required": True, "section": "Assignment Details"},
    {"name": "cy_start_date", "label": "Assignment Start Date", "type": "date",
     "required": True, "section": "Assignment Details"},
    {"name": "cy_end_date", "label": "Assignment End-Date", "type": "date",
     "required": True, "section": "Assignment Details"},
    {"name": "cy_contract_type", "label": "Assignment Contract Type",
     "type": "select", "options": CONSULTANCY_CONTRACT_TYPES, "required": True,
     "section": "Assignment Details",
     "help": "Select the contract type for this assignment. (Click for guidance.)"},
    {"name": "cy_location", "label": "Assignment Location", "type": "text",
     "required": True, "section": "Assignment Details"},
    # Pay Details (rate / currency / frequency) rendered as a row in the template.
    {"name": "cy_rate_of_pay", "label": "Rate of Pay", "type": "number",
     "required": True, "section": "Assignment Details"},
    {"name": "cy_currency", "label": "Currency", "type": "select",
     "options": PAY_CURRENCIES, "required": True, "section": "Assignment Details"},
    {"name": "cy_frequency", "label": "Frequency", "type": "select",
     "options": PAY_FREQUENCIES, "required": True, "section": "Assignment Details"},
    # Select with `fulltext`: the full chosen option is echoed below the dropdown
    # (the long options would otherwise be truncated in the select box).
    {"name": "cy_vat_status", "label": "VAT status determination",
     "type": "select", "options": VAT_STATUS_OPTIONS, "required": True,
     "fulltext": True, "section": "Assignment Details",
     "help": "Determine the VAT status for this consultancy. (Click for guidance.)"},
    {"name": "cy_additional_pay", "label": "Additional pay details",
     "type": "textarea", "section": "Assignment Details",
     "help": "Any additional pay arrangements, allowances or notes."},
    {"name": "cy_expenses_payable", "label": "Are expenses payable?",
     "type": "radio", "options": YES_NO, "required": True,
     "section": "Assignment Details"},
    {"name": "cy_expenses_detail", "label": "Details of expenses payable",
     "type": "textarea", "section": "Assignment Details",
     "show_when": ("cy_expenses_payable", "Yes")},
    # --- Consultant Details ---
    {"name": "cy_named_consultant",
     "label": "Do you have a named consultant for this assignment?",
     "type": "radio", "options": YES_NO, "required": True,
     "section": "Consultant Details"},
    # Named consultant = Yes.
    {"name": "cy_consultant_name", "label": "Name of Consultant", "type": "text",
     "section": "Consultant Details",
     "show_when": ("cy_named_consultant", "Yes")},
    {"name": "cy_consultant_chosen", "label": "How was the consultant chosen?",
     "type": "textarea", "section": "Consultant Details",
     "show_when": ("cy_named_consultant", "Yes")},
    # Named consultant = No -> recruitment branch (defaults No).
    {"name": "cy_hr_advertise",
     "label": "Do you require LSTM HR Recruitment Team to advertise for this "
              "Consultancy?",
     "type": "radio", "options": YES_NO, "default": "No", "required": True,
     "section": "Consultant Details",
     "show_when": ("cy_named_consultant", "No")},
    {"name": "cy_advert_source", "label": "Suggested source for advertisement",
     "type": "textarea", "section": "Consultant Details",
     "show_when": ("cy_hr_advertise", "Yes")},
    {"name": "cy_recruit_budget",
     "label": "Is there a budget available for recruitment purposes?",
     "type": "radio", "options": YES_NO, "default": "No", "required": True,
     "section": "Consultant Details",
     "show_when": ("cy_hr_advertise", "Yes")},
    {"name": "cy_recruit_budget_amount", "label": "Please enter recruitment budget",
     "type": "text", "section": "Consultant Details",
     "show_when": ("cy_recruit_budget", "Yes")},
    {"name": "cy_personal_data",
     "label": "Will the consultant be accessing personal data in the course of "
              "their duties?",
     "type": "radio", "options": YES_NO, "required": True,
     "section": "Consultant Details",
     "help": "Will the consultant access personal/special-category data while "
             "carrying out the work?"},
    {"name": "cy_child_contact",
     "label": "Will this role have direct or indirect contact with children "
              "and/or vulnerable adults?",
     "type": "radio", "options": YES_NO, "required": True,
     "section": "Consultant Details"},
    {"name": "cy_child_contact_detail", "label": "Please provide details",
     "type": "textarea", "section": "Consultant Details",
     "show_when": ("cy_child_contact", "Yes")},
]

STEPS.append(Step("consultancy", "Consultancy",
                  condition=lambda a: a.get("purpose") == "Consultancy",
                  fields=_consultancy_fields))

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

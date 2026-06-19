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
    # Explicit template name (else app.py falls back to step_<id>.html / step.html).
    template: str = ""
    # Approval/workflow stages (stage=True) are NOT part of the requester wizard;
    # active_steps() excludes them. They become the approval chain in Phase 3.
    stage: bool = False


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
    answered 'Yes' to 'add an additional funding source'. Finance Approval n
    reuses this."""
    def cond(answers):
        if n == 1:
            return True
        return answers.get(f"add_funding_{n}") == "Yes"
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
# Short labels shown in the dropdown; the full descriptive wording is the stored
# value (so the record/summary keeps the exact text). Options may be a plain
# string or a {"label", "value"} pair.
VAT_STATUS_OPTIONS = [
    {"label": "Not applicable — exempt service",
     "value": "VAT not applicable due to exempt service being provided"},
    {"label": "Subject to VAT — provided overseas (reverse charge)",
     "value": "Service is subject to VAT but as service is provided overseas "
              "there is no VAT on invoice (but reverse charge VAT will be applied)"},
    {"label": "Subject to VAT — provided in the UK (VAT on invoice)",
     "value": "Service is subject to VAT and provided in the UK so VAT on invoice"}]
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
    {"name": "cy_vat_status", "label": "VAT status determination",
     "type": "select", "options": VAT_STATUS_OPTIONS, "required": True,
     "section": "Assignment Details",
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

# 3. Sources of Funding 1-5 (each can spawn the next).
#    Cost Centre is backed by the OnTrack SharePoint Cost Centre list (the same
#    list the Catering workflow uses), filtered to those authorised to the Line
#    Manager; options are fetched in app.py and rendered server-side. The
#    "add an additional funding source?" question appears only while the running
#    % of total funding is below 100 (numeric `show_when_lt`).
for n in range(1, 6):
    f = [
        {"name": f"funding_cost_centre_{n}", "label": "Cost Centre",
         "type": "select", "options": [], "required": True,
         "widget": "cost_centre",
         "help": "Select the cost centre to be charged. Sourced from the OnTrack "
                 "Cost Centre list (those authorised to the Line Manager)."},
        {"name": f"funding_account_title_{n}", "label": "Account Title",
         "type": "text", "required": True},
        {"name": f"funding_cc_type_{n}", "label": "Cost Centre Type",
         "type": "text", "required": True},
        # Hidden: the RBPS Approver, auto-filled (server-authoritative) from the
        # chosen Cost Centre's "Finance Contact Name" column. Drives finance routing.
        {"name": f"funding_rbps_approver_{n}", "label": "RBPS Approver",
         "type": "hidden"},
        # Hidden: LSTM Finance Approval. Placeholder value 'FBP' for now (to be
        # refined). Shown (read-only) only when the Cost Centre Type is NOT
        # "Research" — the inverse of the RBPS Approver field.
        {"name": f"funding_lstm_finance_{n}", "label": "LSTM Finance Approval",
         "type": "hidden"},
        {"name": f"funding_pct_{n}", "label": "% of total funding",
         "type": "number", "required": True},
        {"name": f"funding_start_{n}", "label": "Funding start-date",
         "type": "date", "required": True},
        {"name": f"funding_end_{n}", "label": "Funding end-date",
         "type": "date", "required": True},
    ]
    if n < 5:
        # Yes/No, defaults No (so it's satisfied while hidden — avoids the
        # hidden-required pitfall). Shown only when this source's % < 100.
        f.append({"name": f"add_funding_{n + 1}",
                  "label": "Do you need to add an additional funding source?",
                  "type": "radio", "options": YES_NO, "default": "No",
                  "required": True,
                  "show_when_lt": (f"funding_pct_{n}", 100)})
    STEPS.append(Step(f"funding_{n}", f"Source of Funding {n}",
                      fields=f, condition=funding_active(n),
                      template="step_funding.html"))

# 4. Approval chain — these are workflow STAGES, not requester wizard pages
#    (stage=True), so active_steps() excludes them. They are routed to the
#    relevant approvers in Phase 3; the field sets are kept for that.
STEPS.append(Step("line_approval", "Line Approval Manager",
                  fields=approval_fields("line"), stage=True))
STEPS.append(Step("director_approval", "Director/Head of Department Approval",
                  fields=approval_fields("director"), stage=True))

# Finance Approval 1-5 — one per active funding source
for n in range(1, 6):
    STEPS.append(Step(f"finance_approval_{n}", f"Finance Approval {n}",
                      fields=approval_fields(f"finance_{n}"),
                      condition=funding_active(n), stage=True))

STEPS.append(Step("head_mgmt_accounting", "Head of Management Accounting Approval",
                  fields=approval_fields("head_mgmt"), stage=True))
STEPS.append(Step("head_rms", "Head of RMS Approval",
                  fields=approval_fields("head_rms"), stage=True))
STEPS.append(Step("hr_signoff", "HR Sign-off",
                  fields=approval_fields("hr_signoff"), stage=True))
STEPS.append(Step("hr_processing", "HR Processing", stage=True,
                  fields=[
                      {"name": "hr_ref", "label": "HR reference number", "type": "text"},
                      {"name": "hr_notes", "label": "Processing notes", "type": "textarea"},
                  ]))


# ---------------------------------------------------------------------------
# Per-type field manifest — the iTrent field spec
# ---------------------------------------------------------------------------
# The four iTrent/Ergo BPM documents are the SPEC for what each A2A type must
# capture (we do NOT generate/email them — the A2A record is central — but the
# downstream iTrent form needs these exact data points). This manifest records,
# per type, each field the document requires mapped to the wizard field that
# supplies it; field == "" marks a GAP the wizard does not yet capture. It
# formalises how the four types differ and is the traceability for the eventual
# iTrent hand-off. Storage is unchanged: answers are a JSON blob on
# a2a_requests keyed by `purpose`.
#
# Layer:  "capture"  — entered by the requester in the wizard (differs by type);
#         "approval" — filled by the approval chain in Phase 3 (stage steps);
#         "process"  — HR sign-off / processing.

# Which document defines each type's field set.
ITRENT_DOCS = {
    "New Position": "iTrent New Position.docx",
    "Replacement":  "A2A Replacement DRAFT.docx",
    "Extension":    "A2A Extension DRAFT.docx",
    "Consultancy":  "A2A Consultancy DRAFT.docx",
}


def _cap(doc: str, field: str) -> dict:
    """A capture-layer manifest entry (doc field -> wizard field; '' = gap)."""
    return {"doc": doc, "field": field, "layer": "capture"}


# Funding sources 1-5 are identical across every type (<n> = source number).
_FUNDING_MANIFEST = [
    _cap("Cost Centre",        "funding_cost_centre_<n>"),
    _cap("Cost Centre Type",   "funding_cc_type_<n>"),
    _cap("% of total funding", "funding_pct_<n>"),
    _cap("Funding start-date", "funding_start_<n>"),
    _cap("Funding end-date",   "funding_end_<n>"),
]

# Capture-layer field set per type (the part that distinguishes the four).
TYPE_FIELDS = {
    "New Position": [
        _cap("Line Manager", "line_manager"),
        _cap("Department", "department"),
        _cap("Job Title", "np_job_title"),
        _cap("Position Location", "np_location"),
        _cap("Appointment term (Permanent / Fixed-term)", ""),       # GAP
        _cap("Please state reasons for fixed-term contract", ""),    # GAP
        _cap("Position end-date (if fixed-term)", ""),               # GAP
        _cap("Position classification", "np_classification"),
        _cap("Contract Basis", "np_contract_basis"),
        _cap("Number of hours worked per week", "np_part_time_hours"),
        _cap("Payscale", "np_payscale"),
        _cap("Grade and/or Salary", "np_grade"),
        _cap("Does this role include clinical duties?", "np_clinical_duties"),
    ] + _FUNDING_MANIFEST,
    "Replacement": [
        _cap("Replacement type", "rp_replacement_type"),
        _cap("Name of person being replaced", "rp_name_replaced"),
        _cap("Department", "department"),
        _cap("Line Manager", "line_manager"),
        _cap("Director/Head of Department", ""),                     # GAP (parked)
        _cap("Justification for Replacement", "rp_justification"),
        _cap("Job Title", "rp_job_title"),
        _cap("Appointment term (Permanent / Fixed-term)", ""),       # GAP
        _cap("Please state reasons for fixed-term contract", ""),    # GAP
        _cap("Estimated start-date of replacement", "rp_start_date"),
        _cap("End-date (if fixed-term)", ""),                        # GAP
        _cap("Payscale", "rp_payscale"),
        _cap("Grade", "rp_grade"),
        _cap("Spinal Point", "rp_spinal_point"),
        _cap("Position Location", "rp_location"),
        _cap("Position Classification", "rp_classification"),
        _cap("Position classification code", "rp_classification_code"),
        _cap("Does this role include clinical duties?", "rp_clinical_duties"),
        _cap("Contact with children/vulnerable adults?", "rp_child_contact"),
        _cap("Number of hours to be worked per week", "rp_part_time_hours"),
        _cap("Working pattern (Mon-Sun)", "rp_hours_<day>"),
    ] + _FUNDING_MANIFEST,
    "Extension": [
        _cap("Purpose of Request", "ex_request_type"),
        _cap("Employee/agency worker name", "ex_employee_name"),
        _cap("Department", "department"),
        _cap("Line Manager", "line_manager"),
        _cap("Director/Head of Department", ""),                     # GAP (parked)
        _cap("Justification", "ex_justification"),
        _cap("Job Title", "ex_job_title"),
        _cap("Extension from", "ex_extension_from"),
        _cap("Extension to", "ex_extension_to"),
        _cap("Proposed weekly working hours", "ex_part_time_hours"),
        _cap("Working pattern (Mon-Sun)", "ex_hours_<day>"),
        _cap("Change to grade", "ex_grade_change"),
        _cap("Change to spinal point", "ex_spinal_point_change"),
        _cap("Work location (city/country)", "ex_location"),
        _cap("Effective date of change to working hours",
             "ex_hours_effective_date"),
        _cap("Is this an ongoing or temporary change?", "ex_change_duration"),
        _cap("Further details (temporary change)", "ex_change_details"),
        _cap("Affect person's other position(s)?", "ex_other_positions_detail"),
    ] + _FUNDING_MANIFEST,
    "Consultancy": [
        _cap("Department", "department"),
        _cap("Approval required for", "cy_approval_for"),
        _cap("Name of Consultant", "cy_consultant_name"),
        _cap("Assignment Overseer Name", "cy_overseer_name"),
        _cap("LSTM Manager Name", "cy_lstm_manager"),
        _cap("Director/Head of Department", ""),                     # GAP (parked)
        _cap("Justification for Consultancy", "cy_justification"),
        _cap("Assignment Job Title", "cy_job_title"),
        _cap("Assignment Start Date", "cy_start_date"),
        _cap("Assignment End-Date", "cy_end_date"),
        _cap("Assignment Location Type", ""),                        # GAP
        _cap("Assignment Location", "cy_location"),
        _cap("Rate of Pay", "cy_rate_of_pay"),
        _cap("Currency", "cy_currency"),
        _cap("Frequency", "cy_frequency"),
        _cap("VAT status determination", "cy_vat_status"),
        _cap("Are expenses payable?", "cy_expenses_payable"),
        _cap("Details of expenses payable", "cy_expenses_detail"),
        _cap("Do you have a named consultant?", "cy_named_consultant"),
        _cap("How was the consultant chosen?", "cy_consultant_chosen"),
        _cap("Require HR to advertise?", "cy_hr_advertise"),
        _cap("Budget available for recruitment?", "cy_recruit_budget"),
        _cap("Recruitment budget", "cy_recruit_budget_amount"),
        _cap("Suggested sources for advertisement", "cy_advert_source"),
        _cap("Will the consultant access personal data?", "cy_personal_data"),
        _cap("Contact with children/vulnerable adults?", "cy_child_contact"),
        _cap("Please provide details", "cy_child_contact_detail"),
    ] + _FUNDING_MANIFEST,
}

# Approval + processing layer — near-identical across all four documents; filled
# by the stage steps in Phase 3, not the requester. NB the documents also
# require an SMG/MC sign-off, for which there is no stage step yet (GAP).
APPROVAL_MANIFEST = [
    {"doc": "Line Manager approval",                 "field": "line_*",        "layer": "approval"},
    {"doc": "Director/Head of Department approval",   "field": "director_*",    "layer": "approval"},
    {"doc": "Finance approver (per funding source)",  "field": "finance_<n>_*", "layer": "approval"},
    {"doc": "Head of Management Accounting approval",  "field": "head_mgmt_*",   "layer": "approval"},
    {"doc": "Head of RMS approval",                   "field": "head_rms_*",    "layer": "approval"},
    {"doc": "SMG/MC sign-off",                        "field": "",              "layer": "approval"},  # GAP: no stage step
    {"doc": "HR sign-off",                            "field": "hr_signoff_*",  "layer": "process"},
    {"doc": "A2A to be processed by / comments",      "field": "hr_ref, hr_notes", "layer": "process"},
]


def manifest_gaps() -> dict:
    """Per type, the capture-layer fields the documents require but the wizard
    does not yet collect (field == ''). Drives the Phase-2 gap list."""
    return {
        t: [e["doc"] for e in entries
            if e["layer"] == "capture" and not e["field"]]
        for t, entries in TYPE_FIELDS.items()
    }


# ---------------------------------------------------------------------------
# Engine helpers
# ---------------------------------------------------------------------------
def active_steps(answers: dict) -> list:
    """The requester wizard: live steps in order, excluding approval stages."""
    return [s for s in STEPS if not s.stage and s.condition(answers)]


def stage_steps(answers: dict) -> list:
    """The approval chain (stage steps) live for these answers, in order."""
    return [s for s in STEPS if s.stage and s.condition(answers)]


def get_step(step_id: str):
    return next((s for s in STEPS if s.id == step_id), None)


def index_of(active: list, step_id: str):
    for i, s in enumerate(active):
        if s.id == step_id:
            return i
    return None

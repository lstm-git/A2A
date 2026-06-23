"""A2A approval orchestration (Phase 3).

Turns a submitted request into per-approver rows and drives the gated, parallel
phases (see steps.PHASES):

    Phase A  : Line Manager + Finance Approval(s)      -- notified on submit
    Phase B  : Head of Mgmt Accounting + Head of RMS   -- on Phase A complete
    HR_SIGNOFF -> HR_PROCESSING                         -- sequential tail

Approvers act via an unguessable per-row token link. A reject / refer-back sends
the request back to the previous step with an email explanation.

Mailboxes are PLACEHOLDERS for now: every fixed role-holder (Finance, Head of
Mgmt Accounting, Head of RMS, HR) and the rejection-explanation email go to
A2A_PLACEHOLDER_EMAIL. Only the Line Manager is a real address (from the form).
"""
import os
import uuid

import dbstore
import notify
import steps as step_engine

PLACEHOLDER_EMAIL = os.environ.get(
    "A2A_PLACEHOLDER_EMAIL", "daniel.williams@lstmed.ac.uk")

# Decision label (from steps.DECISION_CHOICES) -> stored status.
DECISION_STATUS = {"Approve": "approved", "Reject": "rejected",
                   "Refer back": "referred"}

PHASE_LABELS = {
    "A": "Line Manager / Finance approval",
    "B": "Head of Mgmt Accounting / Head of RMS",
    "HR_SIGNOFF": "HR Sign-off",
    "HR_PROCESSING": "HR Processing",
}


def resolve_email(stage_id: str, answers: dict) -> str:
    """The mailbox to notify for a stage. Line Manager comes from the form;
    everything else is a placeholder for now."""
    if stage_id == "line_approval":
        return (answers.get("line_manager") or "").strip() or PLACEHOLDER_EMAIL
    return PLACEHOLDER_EMAIL


def start(ref: str, url_for_token) -> None:
    """Create approval rows for a freshly submitted request and notify its first
    phase. `url_for_token(token)` returns the absolute approve URL."""
    rec = dbstore.get_request(ref)
    if not rec:
        return
    request_id, answers = rec["id"], rec["answers"]
    for s in step_engine.stage_steps(answers):
        dbstore.create_approval(
            request_id=request_id, stage=s.id, role=s.title, phase=s.phase,
            approver_email=resolve_email(s.id, answers), token=uuid.uuid4().hex)
    first = step_engine.first_phase(answers)
    if first:
        _notify_phase(rec, first, url_for_token)


def _notify_phase(rec: dict, phase: str, url_for_token) -> None:
    """Email every not-yet-notified approver in `phase`."""
    for a in dbstore.list_approvals(rec["id"]):
        if a["phase"] != phase or a["notified_at"]:
            continue
        html = notify.approval_request_html(
            ref=rec["ref"], purpose=rec.get("purpose", ""), role=a["role"],
            requester=rec.get("requester", ""),
            approve_url=url_for_token(a["token"]))
        notify.send_email(a["approver_email"],
                          f"A2A {rec['ref']} — approval needed ({a['role']})",
                          html)
        dbstore.mark_notified(a["id"])


def record(token: str, decision: str, comments: str, url_for_token) -> dict:
    """Apply an approver's decision and advance/return the workflow.

    Returns {'ref', 'role', 'status', 'outcome'} where outcome is one of
    'advanced', 'completed', 'returned', or 'noop' (already decided)."""
    a = dbstore.get_approval_by_token(token)
    if not a:
        return {}
    rec = dbstore.get_request_by_id(a["request_id"])
    answers = rec["answers"]
    result = {"ref": rec["ref"], "role": a["role"], "status": a["status"]}

    if a["status"] != "pending":
        result["outcome"] = "noop"
        return result

    status = DECISION_STATUS.get(decision, "approved")
    dbstore.record_decision(token, status, decision, comments)
    result["status"] = status

    if status != "approved":
        # Reject / refer-back: return to the previous step, email an explanation.
        returned_to = _previous_label(answers, a["phase"])
        dbstore.set_request_status(rec["id"], "Returned")
        notify.send_email(
            PLACEHOLDER_EMAIL,
            f"A2A {rec['ref']} — {decision} by {a['role']}",
            notify.rejection_html(rec["ref"], a["role"], decision, comments,
                                  returned_to))
        result["outcome"] = "returned"
        return result

    # Approved — has this completed the phase?
    st = dbstore.phase_status(rec["id"], a["phase"])
    if st["pending"] == 0 and st["blocked"] == 0:
        nxt = step_engine.next_phase(answers, a["phase"])
        if nxt:
            _notify_phase(rec, nxt, url_for_token)
            dbstore.set_request_status(rec["id"], f"In approval ({nxt})")
            result["outcome"] = "advanced"
        else:
            dbstore.set_request_status(rec["id"], "Approved")
            result["outcome"] = "completed"
    else:
        result["outcome"] = "advanced"  # phase still has other approvers pending
    return result


def _previous_label(answers: dict, phase: str) -> str:
    """Human label for the step a rejection returns to (the prior phase, or the
    requester if this is the first phase)."""
    prev = ""
    for p in step_engine.PHASES:
        if p == phase:
            break
        if step_engine.stages_in_phase(answers, p):
            prev = p
    return PHASE_LABELS.get(prev, "the requester") if prev else "the requester"

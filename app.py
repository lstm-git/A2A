"""A2A workflow web app (Flask).

Dynamic multi-step wizard. Answers are held in the browser session only for now
(no database yet). Navigation walks the *active* step list, which is recomputed
from the answers on every request.
"""
import os

from dotenv import load_dotenv
from flask import (Flask, jsonify, redirect, render_template, request,
                   session, url_for)
from werkzeug.middleware.proxy_fix import ProxyFix

load_dotenv()

import dbstore
import graph
import steps as step_engine

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "dev-secret-change-me")

dbstore.init_db()

# Behind the trackon nginx reverse proxy the app is mounted under a sub-path
# (e.g. /A2A). ProxyFix honours the X-Forwarded-Prefix header nginx sends so that
# url_for() and static URLs are generated with that prefix.
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)


def get_answers() -> dict:
    return session.setdefault("answers", {})


def validate_step(step, answers) -> dict:
    """Return {field_name: error_message} for any failed field validations."""
    errors = {}
    for f in step.fields:
        if f.get("validate") == "entra_user":
            value = (answers.get(f["name"], "") or "").strip()
            if value and graph.is_configured() and not graph.user_exists(value):
                errors[f["name"]] = (
                    "No user with that email was found in the tenant.")
    return errors


@app.route("/")
def index():
    session["answers"] = {}
    session.modified = True
    first = step_engine.active_steps({})[0]
    return redirect(url_for("step", step_id=first.id))


@app.route("/step/<step_id>", methods=["GET", "POST"])
def step(step_id):
    current = step_engine.get_step(step_id)
    if current is None:
        return redirect(url_for("index"))

    answers = get_answers()

    errors = {}
    if request.method == "POST":
        for f in current.fields:
            name = f["name"]
            if f["type"] == "checkbox":
                answers[name] = "on" if request.form.get(name) else ""
            else:
                answers[name] = request.form.get(name, "")

        # Departmental Group is derived from Department, never typed.
        if any(f["name"] == "department" for f in current.fields):
            answers["departmental_group"] = step_engine.group_for(
                answers.get("department", ""))

        # Position classification code is derived from the classification choice.
        for f in current.fields:
            if f["name"].endswith("_classification"):
                answers[f["name"] + "_code"] = (
                    step_engine.code_for_classification(
                        answers.get(f["name"], "")))

        # Cost Centre Type and Account Title are derived (server-authoritative)
        # from the chosen Cost Centre's SharePoint record. Fall back to the posted
        # value if the lookup is unavailable (e.g. Graph unconfigured in dev).
        if step_id.startswith("funding_"):
            n = step_id.split("_")[1]
            cc = answers.get(f"funding_cost_centre_{n}", "")
            lm = answers.get("line_manager", "")
            try:
                type_map = graph.cost_centre_type_map(lm)
                account_map = graph.cost_centre_account_map(lm)
                finance_map = graph.cost_centre_finance_map(lm)
            except Exception as exc:
                app.logger.warning("Cost-centre lookup failed: %s", exc)
                type_map = account_map = finance_map = {}
            if cc in type_map:
                answers[f"funding_cc_type_{n}"] = type_map[cc]
            if cc in account_map:
                answers[f"funding_account_title_{n}"] = account_map[cc]
            if cc in finance_map:
                answers[f"funding_rbps_approver_{n}"] = finance_map[cc]
            # LSTM Finance Approval — placeholder routing value for now.
            answers[f"funding_lstm_finance_{n}"] = "FBP"

        session.modified = True

        errors = validate_step(current, answers)
        if step_id.startswith("funding_"):
            errors.update(step_engine.validate_funding(step_id, answers))
        if not errors:
            active = step_engine.active_steps(answers)
            idx = step_engine.index_of(active, step_id)
            if idx is not None and idx + 1 < len(active):
                return redirect(url_for("step", step_id=active[idx + 1].id))
            return redirect(url_for("summary"))

    active = step_engine.active_steps(answers)
    idx = step_engine.index_of(active, step_id)
    prev_id = active[idx - 1].id if idx not in (None, 0) else None

    # Cost Centre dropdown options (funding steps): the OnTrack SharePoint list,
    # filtered to those authorised to the Line Manager chosen on the Purpose page.
    # cost_centre_types maps each cost centre to its Project Type Title, so the
    # read-only Cost Centre Type can auto-fill from the chosen Cost Centre.
    cost_centres = []
    cost_centre_types = {}
    cost_centre_accounts = {}
    cost_centre_finance = {}
    if step_id.startswith("funding_"):
        lm = answers.get("line_manager", "")
        try:
            cost_centres = graph.cost_centres(lm)
            cost_centre_types = graph.cost_centre_type_map(lm)
            cost_centre_accounts = graph.cost_centre_account_map(lm)
            cost_centre_finance = graph.cost_centre_finance_map(lm)
        except Exception as exc:
            app.logger.warning("Cost-centre lookup failed: %s", exc)

    # Template precedence: explicit step.template, else step_<id>.html, else generic.
    custom = current.template or f"step_{step_id}.html"
    template = custom if os.path.exists(
        os.path.join(app.template_folder, custom)) else "step.html"
    return render_template(template, step=current, answers=answers,
                           active=active, prev_id=prev_id, errors=errors,
                           cost_centres=cost_centres,
                           cost_centre_types=cost_centre_types,
                           cost_centre_accounts=cost_centre_accounts,
                           cost_centre_finance=cost_centre_finance,
                           dept_groups=step_engine.DEPARTMENT_TO_GROUP)


@app.route("/api/users/search")
def api_users_search():
    q = request.args.get("q", "").strip()
    try:
        return jsonify(configured=graph.is_configured(),
                       results=graph.search_users(q))
    except Exception as exc:  # surface a clean message to the picker
        app.logger.warning("Graph search failed: %s", exc)
        return jsonify(configured=graph.is_configured(), results=[],
                       error="Directory search failed.")


@app.route("/summary")
def summary():
    answers = get_answers()
    active = step_engine.active_steps(answers)
    return render_template("summary.html", active=active, answers=answers)


@app.route("/submit", methods=["POST"])
def submit():
    """Persist the A2A and show the confirmation. Notifications/PDF come later."""
    answers = get_answers()
    if not answers.get("purpose"):
        return redirect(url_for("index"))
    # Defensive: never persist a part-funded request (per-page validation should
    # already guarantee 100%, but block a hand-crafted POST straight to submit).
    if abs(step_engine.funding_total(answers) - 100) > 1e-9:
        return redirect(url_for("summary"))
    ref = dbstore.create_request(answers)
    session["answers"] = {}  # the request is saved; start a clean session
    session.modified = True
    return redirect(url_for("submitted", ref=ref))


@app.route("/submitted/<ref>")
def submitted(ref):
    record = dbstore.get_request(ref)
    if record is None:
        return redirect(url_for("index"))
    return render_template("submitted.html", record=record)


if __name__ == "__main__":
    host = os.environ.get("HOST", "127.0.0.1")
    port = int(os.environ.get("PORT", 8091))
    app.run(host=host, port=port, debug=True)

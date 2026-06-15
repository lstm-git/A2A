"""A2A workflow web app (Flask).

Dynamic multi-step wizard. Answers are held in the browser session only for now
(no database yet). Navigation walks the *active* step list, which is recomputed
from the answers on every request.
"""
import os

from flask import Flask, render_template, request, redirect, url_for, session

import steps as step_engine

app = Flask(__name__)
app.secret_key = "dev-secret-change-me"  # development only


def get_answers() -> dict:
    return session.setdefault("answers", {})


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

    if request.method == "POST":
        for f in current.fields:
            name = f["name"]
            if f["type"] == "checkbox":
                answers[name] = "on" if request.form.get(name) else ""
            else:
                answers[name] = request.form.get(name, "")
        session.modified = True

        active = step_engine.active_steps(answers)
        idx = step_engine.index_of(active, step_id)
        if idx is not None and idx + 1 < len(active):
            return redirect(url_for("step", step_id=active[idx + 1].id))
        return redirect(url_for("summary"))

    active = step_engine.active_steps(answers)
    idx = step_engine.index_of(active, step_id)
    prev_id = active[idx - 1].id if idx not in (None, 0) else None

    # Use a per-step template (step_<id>.html) if one exists, else the generic one.
    custom = f"step_{step_id}.html"
    template = custom if os.path.exists(
        os.path.join(app.template_folder, custom)) else "step.html"
    return render_template(template, step=current, answers=answers,
                           active=active, prev_id=prev_id)


@app.route("/summary")
def summary():
    answers = get_answers()
    active = step_engine.active_steps(answers)
    return render_template("summary.html", active=active, answers=answers)


if __name__ == "__main__":
    app.run(debug=True, port=5000)

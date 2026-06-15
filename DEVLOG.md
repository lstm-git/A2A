# A2A Dev Log

## 2026-06-15 — Initial scaffold
- New repo `A2A` (nested under ontrack); pushed to github.com/lstm-git/A2A.
- Added Python .gitignore.
- **Decision:** Flask + Jinja, server-rendered (Python-only, no JS build).
- **Decision:** answers held in browser session only for now — no database yet.
- Built a config-driven step engine (`steps.py`): each step has a
  `condition(answers)`; `active_steps()` recomputes the live list each request,
  so answers add/remove later steps dynamically.
- Conditional behaviour wired so far:
  - A2A Purpose (Extension / New Position / Replacement / Consultancy) shows only
    the matching sub-step.
  - Source of Funding 1 always shown; 2–5 appear via an "add another" checkbox.
  - Finance Approval N appears only if Source of Funding N exists (linked).
- Files: `app.py`, `steps.py`, `templates/`, `static/style.css`, `requirements.txt`.
- Field types in templates so far: text, number, date, textarea, radio, select, checkbox.

## 2026-06-15 — Opening page redesign
- Recreated the existing "A2A purpose" opening form with a modern look.
- Expanded `purpose` step fields: Current User (disabled chip, prefilled),
  A2A purpose (select), Department (select — placeholder list), Departmental
  Group (text), Line Manager (chip-style input). All with help tooltips.
- Added per-step custom templates: `app.py` uses `step_<id>.html` if present,
  else generic `step.html`. New `templates/step_purpose.html`.
- Rewrote `static/style.css` with a modern theme (teal/slate, cards, CSS tooltips,
  guidance grid, payroll tags, banners). Generic step page restyled to match.
- **Placeholder:** Department list and the help-tooltip wording need the real values.

## 2026-06-15 — Line Manager Entra ID integration
- **Decision:** type-ahead people picker + app-only (client credentials) Graph auth.
- Added full department list (18) to the dropdown.
- `graph.py`: MSAL ConfidentialClientApplication, token cache, `search_users()`
  and `user_exists()` (Graph `/users`). Reads TENANT_ID/CLIENT_ID/CLIENT_SECRET
  from env (.env via python-dotenv). Degrades gracefully when unconfigured.
- `app.py`: `/api/users/search` endpoint for the picker; `validate_step()` blocks
  submit if a `validate: entra_user` field doesn't resolve in the tenant (skipped
  when Graph not configured). Errors passed to templates.
- Line Manager field is now a picker (`static/picker.js`, debounced search, chip
  selection, manual-entry fallback). CSS added for picker + field errors.
- New deps: requests, python-dotenv. `.env.example` added.

## 2026-06-15 — Reuse Room Booking Entra setup
- Aligned with ontrack-api/blueprints/entra.py to reuse the same app registration.
- `graph.py`: dropped msal; now posts to the token endpoint directly. Env vars
  renamed to `ENTRA_TENANT_ID/ENTRA_CLIENT_ID/ENTRA_CLIENT_SECRET` (match Room
  Booking). Ported their tuned search (startswith mail/UPN for emails, $search
  for names, filtered to @lstmed.ac.uk). `user_exists` via GET /users/{email}.
- **TODO (you):** copy the three ENTRA_* secret values from the ontrack-api
  environment on the VM into A2A's `.env`. No new app registration/consent needed.

### Still to decide / build
- "Completed A2As" — treated as a list view to build later, not a wizard step.
- Per-step vs combined pages (currently one page per step).
- Validation (required fields), persistence (DB), authentication.

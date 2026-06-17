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

## 2026-06-15 — Deployment to VM
- Cloned to `/opt/trackon/A2A` on the VM (nested repo, mirrors local layout).
- `.env` created on the VM only (gitignored); ENTRA_* values copied from
  `/opt/ontrack-api/.env`. Entra people-picker confirmed working live.
- `app.py` port now configurable via HOST/PORT env (default 127.0.0.1:8091),
  since 5000 is taken by ontrack-api.
- Added `a2a.service` (systemd, runs as www-data) and `DEPLOY.md`.
- **TODO:** add reverse-proxy route to 127.0.0.1:8091; install the service.

### Before go-live (REQUIRED)
- **Reverse proxy:** nginx has no route to A2A yet, so it's not browser-reachable.
  Must add an nginx config before go-live. Decision pending: own subdomain
  (e.g. a2a.trackon.lstmed.ac.uk → proxy to 127.0.0.1:8091, no app changes —
  recommended) vs subpath /a2a/ (needs nginx + Flask prefix-awareness, since A2A
  is a multi-page UI that generates its own links). Deferred 2026-06-15.
- **Service / permissions:** install a2a.service and `chown -R www-data` the app
  dir + venv so the service user can read them (only needed once run as a service).

## 2026-06-16 — Service not reachable on VM IP
- **Symptom:** site loaded yesterday, today `http://10.18.0.145:8091/` unreachable
  though `a2a` was running + enabled.
- **Cause:** `a2a.service` set `HOST=127.0.0.1`, so Flask only bound loopback;
  the VM IP rejected connections. (App was healthy — `curl 127.0.0.1:8091` = 302.)
- **Fix:** changed `HOST` to `0.0.0.0`. On the VM: edited
  `/etc/systemd/system/a2a.service`, `daemon-reload` + `restart`; verified
  `ss -ltnp` now shows `0.0.0.0:8091`. Committed same change to repo `a2a.service`
  (commit 94a8a79) so redeploys don't reset it. Confirmed VM IP is on ens33,
  ufw inactive.
- **Note:** binding to 0.0.0.0 exposes the app directly on the VM IP (no proxy);
  acceptable on the trusted network. Reverse-proxy go-live item below still stands.

## 2026-06-16 — New Position screen built out
- Expanded the `new_position` step from 3 placeholder fields to the full form in
  the supplied screenshot (22 fields), split into two sections:
  - **Position Details:** Position Type (Staff/Agency/Work Placement), Job Title,
    Position Location, Payscale (9-option HERA/Clinical/NHS list), Grade (text),
    Spinal Point (text), Position classification (Teaching/Research/etc), classification
    code, Contract Basis (Full-time 35h / Part-time), Mon–Sun working-pattern hours,
    start-date, children/vulnerable-adults contact (Yes/No), Justification.
  - **Recruitment Information:** recruitment-budget (Yes/No), advertising cost centre,
    suggested advert sources.
- **Decision (you):** dropdown option lists supplied by user; Grade & Spinal Point
  kept as free-text; working pattern = 7 hours-per-day inputs.
- **Department & Line Manager auto-populated** from the Purpose page — shown read-only
  (not re-declared as fields, so they can't be overwritten; values live in session).
- **Attachments:** placeholder row only, clearly marked on the form — no file
  storage/upload yet. **TODO:** wire up upload once a DB/storage decision is made.
- New `templates/step_new_position.html` (custom, section bars + work-pattern grid);
  CSS added for `.section-bar`, `.readonly-field`, `.workpattern`, `.attach-placeholder`,
  inline radios. Render verified via Flask test context (no Jinja errors).

## 2026-06-16 — Departmental Group auto-derived from Department
- Departmental Group is no longer typed — it's derived from the selected Department.
- Mapping (source of truth in `steps.py` `DEPARTMENT_GROUPS`):
  - Biological Sciences ← Tropical Disease Biology, Vector Biology
  - Clinical Sciences and International Public Health ← Clinical Sciences, Intl Public Health
  - COO's Office ← COO's Office, Estates, Financial Services, Research Services,
    IT Services, Enterprise and Innovation, Strategic Planning, Legal and Governance,
    Health and Safety
  - Professional Services ← External Relations, Vice-Chancellor's Office, Human
    Resources, Research and Education Facilities
  - Education ← Education
- `steps.group_for()` + flattened `DEPARTMENT_TO_GROUP`. All 18 departments covered.
- **Server-side is authoritative:** `app.py` sets `departmental_group` from `group_for()`
  on submit of any step containing a `department` field. Field on the form is now a
  read-only display + hidden input; a small inline script updates it live on dropdown
  change (map passed to the template via `dept_groups`).

## 2026-06-16 — Replacement screen built out
- Expanded the `replacement` step to the full form in the screenshot (23 fields):
  Replacement type (Staff/Agency) + Name of person being replaced, then
  **Position Details** (Job Title, read-only Department/Line Manager, start-date of
  replacement, Payscale, Grade, Spinal Point, Position Location, hours-per-week,
  optional Mon–Sun working pattern, Position Classification, classification code,
  children/vulnerable-adults contact), **Justification** (Justification for
  Replacement), **Recruitment Information** (budget Yes/No, advert cost centre,
  advert sources), and the attachments placeholder.
- Reuses PAYSCALES / POSITION_CLASSIFICATIONS / YES_NO lists; working pattern is
  optional here ("if known"); fields prefixed `rp_`.
- **Refactor:** pulled the shared rendering into `templates/_form_macros.html`
  (control / row / readonly_row / workpattern / attachments_placeholder) and rewired
  both `step_new_position.html` and `step_replacement.html` to import it, so the two
  screens stay consistent. Both render verified via Flask test context.

## 2026-06-16 — Number fields: positive-only, no spinners
- Hours-per-week and the Mon–Sun working-pattern boxes (New Position + Replacement)
  now reject negatives and have no up/down arrows.
- `_form_macros.html`: number inputs get `min="0"` + `inputmode="decimal"`.
- `style.css`: spinner arrows hidden on `.a2a-form input[type=number]`.
- `picker.js`: blocks `-`/`+`/`e` keys and strips pasted minus on those inputs.
- Decimals still allowed (e.g. 7.5 hours).

## 2026-06-16 — Working-pattern limits + classification code/clinical-duties logic
- **Working pattern:** each day box capped at 12h (`max="12"`). A live total shows
  under the grid; where a step has a weekly-hours field (Replacement,
  `rp_hours_per_week`), an entered pattern must sum to it or submit is blocked
  (`setCustomValidity`). Empty/"not known" pattern is allowed.
- **Position classification code** is now derived, read-only: Teaching Only=40,
  Research Only=41, Teaching & Research=42, Other=43. Source of truth
  `steps.CLASSIFICATION_CODES` + `code_for_classification()`; `app.py` sets
  `<x>_classification_code` on submit; live JS fills the display.
- **Clinical duties follow-up:** "Does this role include Clinical Duties? (Yes/No)"
  appears only when classification = Other (`show_when` metadata; rendered hidden
  and toggled by JS). Applies to both New Position and Replacement.
- New shared macros `classification_code` + `clinical_row` in `_form_macros.html`;
  JS additions in `picker.js`; `.wp-total` styling. Both screens render-verified.

## 2026-06-16 — Recruitment budget follow-up + generic conditional rows
- "Is there a budget available for recruitment purposes?" = **Yes** now reveals a
  follow-up **"Please enter recruitment budget"** (number, £). Fields
  `np_recruit_budget_amount` / `rp_recruit_budget_amount`, `show_when` = (budget, Yes).
- Generalised the clinical-duties toggle into a reusable `conditional_row(trigger,
  value, field, …)` macro + a generic `[data-show-when]` JS handler (radios & selects).
  Clinical-duties follow-up now uses the same mechanism. Both screens render-verified.

## 2026-06-16 — Wired into trackon hub at /A2A/
- **Decision:** serve A2A as a sub-path of the existing site,
  `https://trackon.lstmed.ac.uk/A2A/` (reuses domain + wildcard cert; no DNS/cert
  work) rather than a subdomain. Unlike the 3 static apps, A2A is a live Flask
  service, so it needs a reverse-proxy route (like `/catering/` but → port 8091).
- **A2A app (this repo):** added `ProxyFix(x_prefix=1)` so `url_for`/static honour
  nginx's `X-Forwarded-Prefix` and build links under `/A2A`. base.html now exposes
  `window.A2A_ROOT = request.script_root`; picker.js uses it for the `/api/users/
  search` fetch (the only hard-coded absolute path). Verified via test client with
  the forwarded headers.
- **trackon repo (parent):** added `location /A2A/` block to
  `Catering_orders/ontrack-nginx.conf` (proxy_pass to 127.0.0.1:8091/ with trailing
  slash + X-Forwarded-Prefix /A2A); added a "A2A — Authority to Appoint" card to
  `index.html` linking to `A2A/`.
- **Deploy:** see DEPLOY.md "Reverse proxy / hub" section.

## 2026-06-17 — Hours field unified + working-pattern check on both screens
- **Goal:** make "hours to be worked" identical on New Position and Replacement,
  and enforce the working-pattern sum check on both (previously only Replacement).
- **Hours field (both screens):** a **Contract Basis** dropdown (Full-time (35h) /
  Part-time). Selecting **Part-time** reveals a number field "number of hours to be
  worked per week" (`*_part_time_hours`, optional, via the existing `show_when`).
  Replacement's old free-number `rp_hours_per_week` removed; New Position keeps its
  `np_contract_basis` and gains `np_part_time_hours`.
- **Working pattern (both screens):** now **required** and must sum to the weekly
  target. Target resolved client-side: Full-time → the number parsed from the option
  label (35); Part-time → the entered part-time hours (no check until entered, since
  that field is optional). `workpattern` macro gained `basis`/`pthours` params
  (data-attrs); `picker.js` computes the target, shows a live total, and blocks
  submit if the pattern is empty or doesn't match. Old single `perweek` path kept as
  a fallback.
- Files: `steps.py`, `templates/_form_macros.html`, `templates/step_new_position.html`,
  `templates/step_replacement.html`, `static/picker.js`. Both templates render-verified.
- **Decisions (you):** part-time hours optional; working pattern always required.

### Still to decide / build
- "Completed A2As" — treated as a list view to build later, not a wizard step.
- Per-step vs combined pages (currently one page per step).
- Validation (required fields), persistence (DB), authentication.

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

## 2026-06-17 — Extension screen built out
- Replaced the 3-field Extension placeholder (post/reason/end-date) with the full
  form from the supplied screenshot. Fields prefixed `ex_`, three sections:
  - **Person Details:** Employee/agency worker name, Job Title, read-only
    Department + Line Manager (carried from Purpose). Purpose of Request shown
    read-only at the top.
  - **Details of extension/hours change:** Contract Basis (Full-time/Part-time) +
    conditional part-time hours + required working pattern — **uniform with New
    Position / Replacement** (per your choice). Then grade-change, spinal-point-change
    (free text, "or No change"), work location (city/country).
  - **Justification:** Justification + attachments placeholder.
- **Structure note:** the Extension step is now defined *after* the shared constants
  (CONTRACT_BASES / WORK_PATTERN_DAYS) in `steps.py`, since it reuses them; the early
  placeholder append was removed. Wizard order unchanged (Purpose → Extension → …).
- New `templates/step_extension.html`; render-verified.

## 2026-06-17 — Extension: Purpose-of-Request dropdown + conditional questions
- Purpose of Request is now a required dropdown (`ex_request_type`) with 5 options;
  each drives which follow-up questions show:
  - **Conversion of fixed term contract to Permanent:** Extension from, Extension
    to, Current fixed-term contract end date.
  - **Extension of fixed-term / agency / funding (permanent):** Extension from,
    Extension to (the same two; shown for all three).
  - **Change to weekly working hours only (no contract extension):** Effective date
    of change to working hours; "Is this an ongoing or temporary change?"
    (Ongoing/Temporary — Temporary reveals "Please provide further details");
    "Does this person have more than 1 position?" (Yes/No — Yes reveals "…affect
    the person's other positions in any way").
- **Mechanism:** new `conditional_field` macro reads each field's own `show_when`
  metadata `(trigger, value|[values])`, so a row can show for **several** trigger
  values (Extension from/to use the 4-value list `EXTENSION_DATE_PURPOSES`). The
  `[data-show-when]` JS now tests list membership (values joined by `||`) and, when a
  row hides, **clears its inputs and fires change/input** so nested conditionals
  (Temporary → details, Yes → other-positions) collapse with their parent.
- Conditional fields left **optional** (consistent with existing clinical-duties /
  recruit-budget follow-ups — the generic show_when JS doesn't manage `required` on
  hidden fields).
- Files: `steps.py` (constants + 8 conditional fields), `_form_macros.html`
  (`conditional_field`), `static/picker.js`, `templates/step_extension.html`.
  Server-side initial show/hide verified across all purposes.

## 2026-06-17 — Consultancy screen built out
- Built the full Consultancy page from the supplied screenshot (`cy_` prefix,
  custom `templates/step_consultancy.html`):
  - **Top:** Approval required for (select), read-only Department (carried over),
    Justification for Consultancy, Assignment Overseer Name, LSTM Manager Name.
  - **Assignment Details:** Job Title, Start Date, End-Date, Contract Type (select,
    help), Location, **Pay Details** (Rate of Pay / Currency / Frequency on one row
    via a `.paydetails` table), VAT status determination (select, help), Additional
    pay details (optional), Are expenses payable? (Yes/No).
  - **Consultant Details:** Do you have a named consultant? / Will the consultant be
    accessing personal data? (help) / contact with children & vulnerable adults?
    (all Yes/No), then the required-documentation block: a yellow `banner note`
    listing the four docs (ToR, two Status Determination forms, Consultant's CV) +
    the existing attachments placeholder (upload still not built).
- New `.paydetails` table CSS (matches `.workpattern`).
- **Placeholder option lists (need real values):** `CONSULTANCY_APPROVAL_FOR`,
  `CONSULTANCY_CONTRACT_TYPES`, `VAT_STATUS_OPTIONS`, `PAY_CURRENCIES`,
  `PAY_FREQUENCIES` in `steps.py` are guesses — same situation as the early
  Department list. **TODO (you):** supply the real options + the exact help/tooltip
  wording for the Contract Type / VAT / personal-data info icons.
- Files: `steps.py`, `templates/step_consultancy.html`, `static/style.css`.
  Render-verified (all 18 fields, both sections, pay table, banner present).

## 2026-06-17 — Consultancy: real option lists + conditional logic
- **Real option lists supplied** (replaced placeholders): Assignment Contract Type
  (Contingent Worker / UK Consultancy / Non-UK Consultancy / Contract for Services)
  and VAT status determination (3 long descriptive options). Approval-for / currency
  / frequency lists still placeholders.
- **Conditional questions added** (all via the `show_when` + `conditional_field`
  mechanism, incl. nested cascade):
  - Are expenses payable? **Yes** → Details of expenses payable (textarea).
  - Named consultant? **Yes** → Name of Consultant (text) + How was the consultant
    chosen (textarea). **No** → "Do you require LSTM HR Recruitment Team to advertise…"
    (Yes/No, **default No**); if **Yes** → Suggested source for advertisement
    (textarea) + "Is there a budget…" (Yes/No, **default No**); if that's **Yes** →
    Please enter recruitment budget (text).
  - Children/vulnerable-adults contact? **Yes** → Please provide details (textarea).
- **New: radio `default`** support. `control` macro pre-checks the default option and
  marks it `data-default`; the show-when JS now resets hidden radios to their default
  (not just unchecked), so the "default No" reasserts when a branch collapses.
- Conditional text/textarea fields left optional (hidden-required pitfall); the two
  defaulted Yes/No radios are required but always satisfied by the default.
- Files: `steps.py`, `templates/_form_macros.html`, `static/picker.js`,
  `templates/step_consultancy.html`. All branches render-verified.

## 2026-06-19 — Source of Funding screens rebuilt + SharePoint Cost Centre
- Rebuilt Source of Funding 1-5 to the supplied screenshot (replaced the old 3
  fields). New field set per source: **Cost Centre** (select), Account Title,
  Cost Centre Type, % of total funding, Funding start-date, Funding end-date,
  then **"Do you need to add an additional funding source?"** (Yes/No) and the
  attachments placeholder. Field names `funding_<thing>_<n>`.
- **Cost Centre wired to SharePoint** (you: wire now): `graph.cost_centres(email)`
  reuses the OnTrack Cost Centre list — same site/list-id/fields as the Catering
  workflow (ontrack-api `/entra/cost-centres`); raw list cached 5 min. **Filtered
  by the Line Manager email** (you: A2A has no requester auth yet, so the LM
  chosen on the Purpose page is used as the authorised email). Options rendered
  server-side; `app.py` fetches them for `funding_*` steps and passes
  `cost_centres` to the template. Degrades to "no cost centres available" when
  Graph is unconfigured (dev) or none are authorised.
- **Add-another only when % < 100:** new numeric conditional `show_when_lt:
  (field, threshold)` — macro `numeric_conditional_row` + a `[data-show-when-lt]`
  handler in picker.js (mirrors the equality handler's reset-on-hide). The
  Yes/No radio **defaults No** and is required, so it's satisfied while hidden
  (avoids the hidden-required pitfall) and means "don't add another".
- The add-another control changed from a **checkbox** to **Yes/No radio**;
  `funding_active()` now spawns the next source on `== "Yes"` (was `== "on"`).
  Finance Approval N reuses `funding_active`, so it follows automatically.
- **Engine:** `Step` gained an optional `template` field; `app.py` template
  precedence is now `step.template` -> `step_<id>.html` -> `step.html`. One shared
  `templates/step_funding.html` serves all five (suffix from the step id).
- New macro `cost_centre_row`. Files: `steps.py`, `graph.py`, `app.py`,
  `_form_macros.html`, `templates/step_funding.html`, `static/picker.js`.
- **Verified** via Flask test client: all five render 200; funding_5 has no
  add-another; %50+Yes spawns funding_2 and POST redirects there; %100/No/default
  do not.
- **TODO:** swap the LM-email cost-centre filter for the logged-in requester once
  A2A has auth/SSO.

## 2026-06-19 — Workflow direction decided (central approvals, not emailed docs)
- **Context:** after Funding, a purpose-specific Word doc (example `A2A New
  Position- DRAFT.docx`, content-control placeholders mapping 1:1 to A2A fields)
  was to be generated and emailed round for sign-off.
- **Decision (you):** don't email documents — go **central**. The A2A is the
  record; approvers act in-app; the document becomes an on-demand export.
  Chosen: **in-app approvals**, **email-with-link** notifications, **PDF from
  HTML** (on demand). Approver identity for v1 reuses the **Catering token
  pattern** (per-approver unguessable link, no SSO needed) — corrects an earlier
  "need full Entra SSO" assumption.
- **Build phases:** (1) persistence + submit, (2) PDF generation, (3) approval
  workflow + email, (4) dashboards.
- **Open (Phase 3):** approver routing — Line Manager from the form; **Director/
  HoD captured on the form** (you: I'll place the field — NOT added yet);
  Finance / Head of Mgmt Accounting / Head of RMS / HR are fixed role-holders
  (list TBC). Sequential vs parallel finance approvals TBC. WeasyPrint needs
  pango/cairo on the VM (vs wkhtmltopdf) — TBC.

## 2026-06-19 — Phase 1: persistence + submit
- **`dbstore.py` (new, SQLite):** `a2a_requests` (ref, status, purpose,
  requester, created_at, **answers stored as JSON blob**) + empty `a2a_approvals`
  (Phase 3). Ref format `A2A-0042` (zero-padded row id). `create_request`,
  `get_request`, `list_requests`, `init_db` (called on app start).
  - **Decision (you):** start on SQLite; **keep ALL DB access inside dbstore.py**
    so moving to a server DB (Postgres/SQL Server) in prod is a one-file change.
    DB path overridable via `A2A_DB` env.
- **Approval steps removed from the requester wizard, non-destructively:** new
  `Step.stage` flag; `line/director/finance_*/head_*/hr_*` marked `stage=True`;
  `active_steps()` excludes stage steps (added `stage_steps()` for Phase 3). The
  wizard now ends at the last Source of Funding. Steps kept, not deleted.
- **Submit flow:** Summary page gained a **"Submit for approval"** button →
  `POST /submit` saves the request and clears the session → redirect to new
  **`/submitted/<ref>`** confirmation page (ref + status). New `submitted.html`.
- **Director/HoD field NOT added yet** (you'll decide placement).
- Files: `dbstore.py`, `steps.py`, `app.py`, `templates/summary.html`,
  `templates/submitted.html`, `.gitignore` (a2a.db), `DEPLOY.md`.
- **Verified** (Flask test client, temp DB): wizard excludes stage steps but
  get_step/stage_steps still resolve them; submit persists `A2A-0001`,
  round-trips the answer JSON, redirects to a 200 confirmation, clears session.

## 2026-06-19 — Summary centring + Cost Centre Type auto-fill
- **Summary page centred:** it used `.panel` (max-width but no auto margins, so it
  sat left); switched to the standard `.page` + `.card` wrapper like the other
  screens.
- **Cost Centre Type now auto-fills from the chosen Cost Centre** (you: same
  record, not an independent dropdown). Sourced from the cost-centre list's
  **"Project Type Title"** column.
  - `graph.py`: `_cost_centre_type_field()` resolves that column's internal
    SharePoint name from its display name (cached; falls back to
    `Project_x0020_Type_x0020_Title`); `_cost_centre_items()` now also selects it;
    new `cost_centre_type_map(email)` -> `{cost_centre: project_type}`.
  - `app.py`: passes `cost_centre_types` to the funding template and, on submit,
    sets `funding_cc_type_<n>` from the map (**server-authoritative**, like
    Departmental Group — ignores any tampered hidden value).
  - `step_funding.html`: Cost Centre Type is now a **read-only** display + hidden
    input, auto-filled live by a small inline script from the injected map.
- **Verified** (test client, patched Graph): field is read-only (no free-text box);
  map injected; picking a cost centre fills the type; a tampered POST value is
  overwritten from the record.

## 2026-06-19 — Account Title auto-fills from Cost Centre too
- **Account Title** now auto-fills from the chosen Cost Centre's SharePoint record
  (column **AccountTitle**) — same read-only / server-authoritative pattern as
  Cost Centre Type (was free text).
- `graph.py`: generalised the single type-column resolver into `_cc_columns()`
  (caches the list's display+internal column-name map) + `_cc_field((wanted,
  fallback))`; column specs now `COST_CENTRE_TYPE_COLUMN` / `…_ACCOUNT_COLUMN`.
  `_cost_centre_items()` selects both; new `cost_centre_account_map(email)`.
- `app.py`: passes `cost_centre_accounts` to the funding template and sets
  `funding_account_title_<n>` from the map on submit (alongside cc_type).
- `step_funding.html`: Account Title is now read-only display + hidden input; the
  inline script generalised to `bindDerived(map, baseName)` and fills both Account
  Title and Cost Centre Type on Cost Centre change.
- **Verified** (test client, patched Graph): Account Title read-only, both maps
  injected, tampered POST values for account + type overwritten from the record;
  all modules byte-compile.

### Still to decide / build
- Phase 2 (PDF), Phase 3 (approval workflow + email), Phase 4 (dashboards).
- "Completed A2As" — the dashboard/list view (Phase 4).
- Validation (required fields), authentication (full SSO optional, post-v1).

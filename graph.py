"""Microsoft Graph helper — app-only (client credentials) access to Entra ID.

Mirrors the OnTrack Room Booking integration (ontrack-api/blueprints/entra.py)
so the same app registration and credentials work here. Used to power the Line
Manager people-picker and to validate that an email is a real tenant user.

Config (same names as Room Booking, see .env.example):
    ENTRA_TENANT_ID, ENTRA_CLIENT_ID, ENTRA_CLIENT_SECRET

If those are not set the helper is "not configured": searches return empty and
validation is skipped, so the app still runs in development without credentials.
"""
import os
import threading
import time

import requests

TENANT_ID = os.environ.get("ENTRA_TENANT_ID")
CLIENT_ID = os.environ.get("ENTRA_CLIENT_ID")
CLIENT_SECRET = os.environ.get("ENTRA_CLIENT_SECRET")

GRAPH = "https://graph.microsoft.com/v1.0"
DOMAIN = "@lstmed.ac.uk"
TIMEOUT = 10

# OnTrack SharePoint Cost Centre list — the same list/fields the Catering
# workflow uses (ontrack-api/blueprints/entra.py /cost-centres).
COST_CENTRE_SITE = "lstmed.sharepoint.com:/sites/OnTrack:"
COST_CENTRE_LIST_ID = "F0B05C0A-4E80-41EE-B143-AAA154B92313"
# Extra cost-centre list columns read alongside Title, as (wanted, fallback):
# `wanted` is matched against column display OR internal names at runtime (so a
# rename / odd encoding shouldn't break us); `fallback` is used if columns can't
# be read. Cost Centre Type <- Project Type Title; Account Title <- AccountTitle.
COST_CENTRE_TYPE_COLUMN = ("Project Type Title", "Project_x0020_Type_x0020_Title")
COST_CENTRE_ACCOUNT_COLUMN = ("AccountTitle", "AccountTitle")
# RBPS Approver (hidden) <- Finance Contact Name.
COST_CENTRE_FINANCE_COLUMN = ("Finance Contact Name", "Finance_x0020_Contact_x0020_Name")
COST_CENTRE_TTL = 300  # seconds to cache the raw list

_lock = threading.Lock()
_token = {"value": None, "expires": 0.0}
_cost_centre_cache = {"items": None, "expires": 0.0}
_cc_columns_cache = {"map": None, "expires": 0.0}


def is_configured() -> bool:
    return bool(TENANT_ID and CLIENT_ID and CLIENT_SECRET)


def _token_value() -> str:
    with _lock:
        if _token["value"] and time.time() < _token["expires"] - 60:
            return _token["value"]
        resp = requests.post(
            f"https://login.microsoftonline.com/{TENANT_ID}/oauth2/v2.0/token",
            data={
                "grant_type": "client_credentials",
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "scope": "https://graph.microsoft.com/.default",
            },
            timeout=TIMEOUT,
        )
        resp.raise_for_status()
        data = resp.json()
        _token["value"] = data["access_token"]
        _token["expires"] = time.time() + data["expires_in"]
        return _token["value"]


def search_users(query: str, top: int = 8) -> list[dict]:
    """Return [{name, email}] for tenant users matching name or email.

    Email queries (containing '.' or '@') do a precise startswith on mail and
    UPN; name queries use Graph word-boundary search. Results are limited to the
    LSTM domain, as in Room Booking.
    """
    q = (query or "").strip()
    if not is_configured() or len(q) < 2:
        return []

    token = _token_value()
    url = f"{GRAPH}/users"
    q_safe = q.replace("'", "''")
    select = "displayName,mail,userPrincipalName"

    if "." in q or "@" in q:
        auth = {"Authorization": f"Bearer {token}"}
        r1 = requests.get(url, headers=auth, timeout=TIMEOUT, params={
            "$filter": f"startswith(mail,'{q_safe}')", "$select": select, "$top": "8"})
        r2 = requests.get(url, headers=auth, timeout=TIMEOUT, params={
            "$filter": f"startswith(userPrincipalName,'{q_safe}')",
            "$select": select, "$top": "8"})
        rows = (r1.json().get("value", []) if r1.ok else []) + \
               (r2.json().get("value", []) if r2.ok else [])
    else:
        r = requests.get(url, timeout=TIMEOUT, params={
            "$search": f'"displayName:{q_safe}"', "$select": select,
            "$top": "8", "$count": "true"
        }, headers={"Authorization": f"Bearer {token}",
                    "ConsistencyLevel": "eventual"})
        rows = r.json().get("value", []) if r.ok else []

    seen, users = set(), []
    for u in rows:
        upn = u.get("userPrincipalName", "")
        email = u.get("mail") or upn
        if not email or not email.lower().endswith(DOMAIN):
            continue
        if upn.lower().startswith(q.lower()):
            email = upn
        if email.lower() in seen:
            continue
        seen.add(email.lower())
        users.append({"name": u.get("displayName", "") or email, "email": email})

    return users[:top]


def user_exists(email: str) -> bool:
    """True if the email resolves to a user in the tenant."""
    email = (email or "").strip()
    if not is_configured() or not email:
        return False
    resp = requests.get(
        f"{GRAPH}/users/{email}",
        headers={"Authorization": f"Bearer {_token_value()}"}, timeout=TIMEOUT)
    return resp.status_code == 200


def _cc_columns() -> dict:
    """Cost-centre list columns as {display_or_internal_name_lower: internal}, cached."""
    now = time.time()
    with _lock:
        if _cc_columns_cache["map"] is not None and now < _cc_columns_cache["expires"]:
            return _cc_columns_cache["map"]

    cmap: dict = {}
    try:
        url = (f"{GRAPH}/sites/{COST_CENTRE_SITE}/lists/{COST_CENTRE_LIST_ID}"
               "/columns?$select=name,displayName")
        resp = requests.get(
            url, headers={"Authorization": f"Bearer {_token_value()}"}, timeout=TIMEOUT)
        if resp.ok:
            for col in resp.json().get("value", []):
                nm = col.get("name") or ""
                dn = (col.get("displayName") or "").strip().lower()
                if nm:
                    cmap[nm.lower()] = nm   # internal -> internal
                    if dn:
                        cmap[dn] = nm       # display  -> internal
    except Exception:
        pass  # fall back to per-column defaults

    with _lock:
        _cc_columns_cache["map"] = cmap
        _cc_columns_cache["expires"] = time.time() + COST_CENTRE_TTL
    return cmap


def _cc_field(column: tuple) -> str:
    """Resolve a (wanted, fallback) column spec to its internal field name."""
    wanted, fallback = column
    return _cc_columns().get(wanted.strip().lower(), fallback)


def _cost_centre_items() -> list[dict]:
    """Raw cost-centre rows [{title, authorised, type, account}], cached."""
    now = time.time()
    with _lock:
        if _cost_centre_cache["items"] is not None and now < _cost_centre_cache["expires"]:
            return _cost_centre_cache["items"]

    type_field = _cc_field(COST_CENTRE_TYPE_COLUMN)
    account_field = _cc_field(COST_CENTRE_ACCOUNT_COLUMN)
    finance_field = _cc_field(COST_CENTRE_FINANCE_COLUMN)
    url = (
        f"{GRAPH}/sites/{COST_CENTRE_SITE}/lists/{COST_CENTRE_LIST_ID}/items"
        "?$expand=fields($select=Title,Authorised_x0020_Email_x0020_Add,"
        f"{type_field},{account_field},{finance_field})&$top=500"
    )
    resp = requests.get(
        url, headers={"Authorization": f"Bearer {_token_value()}"}, timeout=TIMEOUT)
    resp.raise_for_status()
    items = []
    for item in resp.json().get("value", []):
        f = item.get("fields", {})
        items.append({
            "title": (f.get("Title") or "").strip(),
            "authorised": (f.get("Authorised_x0020_Email_x0020_Add") or "").lower(),
            "type": (f.get(type_field) or "").strip(),
            "account": (f.get(account_field) or "").strip(),
            "finance": (f.get(finance_field) or "").strip(),
        })

    with _lock:
        _cost_centre_cache["items"] = items
        _cost_centre_cache["expires"] = time.time() + COST_CENTRE_TTL
    return items


def _authorised_items(email: str) -> list[dict]:
    email = (email or "").strip().lower()
    if not is_configured() or not email:
        return []
    return [it for it in _cost_centre_items()
            if it["title"] and email in it["authorised"]]


def cost_centres(email: str) -> list[str]:
    """Cost centres whose 'Authorised Email Add' contains `email` (sorted, unique).

    Mirrors the Catering filter. Returns [] when Graph is unconfigured or no
    email is given (so the dropdown degrades gracefully in development)."""
    return sorted({it["title"] for it in _authorised_items(email)})


def cost_centre_type_map(email: str) -> dict:
    """{cost_centre_title: project_type} for cost centres authorised to `email`.

    Drives the read-only Cost Centre Type, auto-filled from the chosen Cost
    Centre's record. Returns {} when Graph is unconfigured."""
    return {it["title"]: it["type"] for it in _authorised_items(email) if it["title"]}


def cost_centre_account_map(email: str) -> dict:
    """{cost_centre_title: account_title} for cost centres authorised to `email`.

    Drives the read-only Account Title, auto-filled from the chosen Cost Centre's
    record (the list's AccountTitle column). Returns {} when Graph is unconfigured."""
    return {it["title"]: it["account"] for it in _authorised_items(email) if it["title"]}


def cost_centre_finance_map(email: str) -> dict:
    """{cost_centre_title: finance_contact_name} for cost centres authorised to
    `email`.

    Drives the hidden RBPS Approver field, auto-filled from the chosen Cost
    Centre's record (the list's Finance Contact Name column). Returns {} when
    Graph is unconfigured."""
    return {it["title"]: it["finance"] for it in _authorised_items(email) if it["title"]}

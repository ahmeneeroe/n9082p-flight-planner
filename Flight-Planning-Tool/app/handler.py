"""HTTP handler for the N9082P flight planner.

A framework-agnostic core (`handle`) drives both the AWS Lambda Function URL adapter
(`lambda_handler`) and the local dev server (devserver.py), so local behavior matches
production.

Access control: a password gates the app via a signed cookie, set after a login-form
POST. We use a cookie rather than HTTP Basic Auth because Lambda Function URLs remap the
`WWW-Authenticate` response header (to `x-amzn-Remapped-*`), so browsers never show the
Basic Auth dialog. The cookie token is HMAC-signed with the password, so it can't be
forged or reused after a password change. If PLANNER_PASSWORD is unset (local dev), the
app is open.
"""
import base64
import hashlib
import hmac
import os
import sys
import time
import urllib.parse

# Make the project root importable so `planner` resolves regardless of CWD.
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from planner import generate, render  # noqa: E402

COOKIE_NAME = "n9082p_auth"
COOKIE_MAX_AGE = 30 * 86400  # 30 days


def _sign(msg, password):
    return hmac.new(password.encode(), msg.encode(), hashlib.sha256).hexdigest()


def _make_cookie(password):
    exp = str(int(time.time()) + COOKIE_MAX_AGE)
    token = f"{exp}.{_sign(exp, password)}"
    return (f"{COOKIE_NAME}={token}; Path=/; HttpOnly; Secure; SameSite=Lax; "
            f"Max-Age={COOKIE_MAX_AGE}")


def _cookie_jar(headers, cookie_list):
    jar = {}
    for c in (cookie_list or []):
        k, _, v = c.partition("=")
        jar[k.strip()] = v.strip()
    raw = headers.get("cookie") or headers.get("Cookie") or ""
    for part in raw.split(";"):
        if "=" in part:
            k, _, v = part.partition("=")
            jar[k.strip()] = v.strip()
    return jar


def _authed(headers, cookie_list, password):
    token = _cookie_jar(headers, cookie_list).get(COOKIE_NAME, "")
    try:
        exp, sig = token.split(".", 1)
        return hmac.compare_digest(sig, _sign(exp, password)) and int(exp) > time.time()
    except Exception:
        return False


def _opt(params, name, default=None):
    v = params.get(name)
    return v if v not in (None, "") else default


def _safe_next(value):
    return value if (value and value.startswith("/") and not value.startswith("//")) else "/"


def handle(method, query_string, headers, body="", cookie_list=None):
    """Core request handler. Returns (status, headers_dict, body_str).

    headers_dict may include 'set-cookie' and/or 'location'; adapters translate as needed.
    """
    html_hdr = {"content-type": "text/html; charset=utf-8"}
    password = os.environ.get("PLANNER_PASSWORD")

    # Login form submission (the app's only POST).
    if method == "POST":
        form = dict(urllib.parse.parse_qsl(body or ""))
        nxt = _safe_next(form.get("next"))
        if not password:
            return 302, {"location": nxt}, ""
        if hmac.compare_digest(form.get("password", "") or "", password):
            return 302, {"location": nxt, "set-cookie": _make_cookie(password)}, ""
        return 200, html_hdr, render.login_html(error="Incorrect password.", next_url=nxt)

    # Gate everything else on the signed cookie.
    if password and not _authed(headers, cookie_list, password):
        return 200, html_hdr, render.login_html(next_url="/")

    # Authenticated (or no password configured): serve the app.
    params = dict(urllib.parse.parse_qsl(query_string or ""))
    dep = (params.get("dep") or "").strip()
    dest = (params.get("dest") or "").strip()
    if not dep or not dest:
        return 200, html_hdr, render.form_html(params)
    try:
        sheet = generate.build_sheet(
            dep, dest,
            takeoff_weight_lb=float(_opt(params, "weight", 2700)),
            fuel_gal=float(_opt(params, "fuel", 86)),
            cruise_alt_ft=float(_opt(params, "cruise_alt", 7500)),
            power=float(_opt(params, "power", 65)),
            rpm=int(float(_opt(params, "rpm", 2400))),
            mixture=_opt(params, "mixture", "best_economy"),
            landing_weight_lb=(float(params["landing_weight"])
                               if _opt(params, "landing_weight") else None),
        )
        return 200, html_hdr, render.render_html(sheet)
    except generate.AirportNotFound as e:
        return 200, html_hdr, render.error_html(str(e), params)
    except ValueError as e:
        return 200, html_hdr, render.error_html(f"Invalid input: {e}", params)
    except Exception as e:  # never hand a 500 to the pilot -- show what failed
        return 200, html_hdr, render.error_html(f"Could not build sheet: {e}", params)


def lambda_handler(event, context=None):
    """AWS Lambda Function URL adapter (HTTP API payload format 2.0)."""
    rc = event.get("requestContext", {}).get("http", {})
    method = rc.get("method", "GET")
    qs = event.get("rawQueryString", "")
    headers = event.get("headers", {}) or {}
    cookie_list = event.get("cookies")  # payload v2.0 provides cookies as a list
    body = event.get("body", "") or ""
    if event.get("isBase64Encoded") and body:
        body = base64.b64decode(body).decode("utf-8", "replace")

    status, hdrs, out = handle(method, qs, headers, body, cookie_list)
    resp = {"statusCode": status,
            "headers": {k: v for k, v in hdrs.items() if k != "set-cookie"},
            "body": out}
    if "set-cookie" in hdrs:           # Set-Cookie must go in the cookies array, not headers
        resp["cookies"] = [hdrs["set-cookie"]]
    return resp

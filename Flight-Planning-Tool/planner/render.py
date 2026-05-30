"""Render the safety sheet dict (from generate.build_sheet) to A5 HTML.

Reproduces the validated A5 landscape B&W prototype, parameterised. Also provides
the mobile input form and an error page. Pure string templating -- no dependencies.
"""
import html

_CSS = """
@page { size: A5 landscape; margin: 6mm; }
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: -apple-system, 'Helvetica Neue', Arial, sans-serif;
  width: 210mm; margin: 0 auto; padding: 8px; font-size: 11px; line-height: 1.3; color: #000; }
h1 { font-size: 16px; display: inline; }
.route { color: #444; font-size: 12px; display: inline; margin-left: 8px; }
.top-bar { display: flex; justify-content: space-between; align-items: baseline;
  border-bottom: 2px solid #000; padding-bottom: 5px; margin-bottom: 6px; }
.top-params { font-size: 11px; color: #444; }
.warnbar { font-size: 9px; font-weight: 700; text-transform: uppercase; letter-spacing: .3px;
  border: 1px solid #000; padding: 2px 6px; margin-bottom: 8px; text-align: center; }
.cols { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; margin-bottom: 8px; }
.airport { border: 1px solid #888; border-radius: 3px; padding: 6px 8px; }
.apt-header { font-weight: 700; font-size: 13px; margin-bottom: 2px; }
.apt-header .rwy-info { font-weight: 400; font-size: 10px; color: #444; }
.apt-meta { font-size: 10px; color: #444; margin-bottom: 5px; }
.apt-meta b { color: #000; }
table { width: 100%; border-collapse: collapse; font-size: 10px; margin: 3px 0; }
th { text-align: left; font-weight: 600; padding: 2px 5px; border-bottom: 1px solid #888;
  font-size: 8px; color: #444; text-transform: uppercase; }
th.r, td.r { text-align: right; }
td { padding: 2px 5px; }
.sub-header { font-size: 9px; font-weight: 700; text-transform: uppercase; color: #444;
  letter-spacing: 0.3px; margin: 5px 0 2px; }
.badge { display: inline-block; padding: 0 4px; border-radius: 2px; font-size: 8px;
  font-weight: 700; text-transform: uppercase; border: 1px solid #888; }
.badge.ok { background: #fff; }
.badge.cau { background: #ddd; }
.badge.warn { background: #000; color: #fff; border-color: #000; }
.speeds { display: flex; gap: 10px; margin: 3px 0; font-size: 10px; }
.speeds b { font-size: 13px; }
.speeds .highlight { border-bottom: 2px solid #000; }
.remark { font-size: 9px; color: #444; margin-top: 3px; font-style: italic; }
.summary { border: 1px solid #888; border-radius: 3px; padding: 5px 8px; margin-bottom: 4px;
  display: grid; grid-template-columns: repeat(auto-fit, minmax(72px, 1fr)); gap: 3px 10px; font-size: 10px; }
.summary .label { font-size: 7.5px; color: #444; text-transform: uppercase; }
.summary .val { font-weight: 700; font-size: 11px; }
.summary .val.warn { text-decoration: underline; text-decoration-thickness: 1.5px; }
.notes { font-size: 8px; color: #444; border-top: 1px solid #888; padding-top: 3px; margin-top: 3px; }
.actions { margin: 8px 0; font-size: 12px; }
.actions a, .actions button { font: inherit; margin-right: 12px; }
@media screen and (max-width: 760px) { body { width: 100%; } .cols { grid-template-columns: 1fr; } }
@media print { body { padding: 0; width: auto; } .actions { display: none; } }
"""

_BADGE_TEXT = {"ok": "OK", "cau": "CAU", "warn": "WARN"}


def _esc(s):
    return html.escape(str(s)) if s is not None else ""


def _badge(b):
    return f'<span class="badge {b}">{_BADGE_TEXT.get(b, b.upper())}</span>'


def _page(title, body):
    return (f'<!DOCTYPE html><html lang="en"><head><meta charset="UTF-8">'
            f'<meta name="viewport" content="width=device-width, initial-scale=1.0">'
            f'<title>{_esc(title)}</title><style>{_CSS}</style></head><body>{body}</body></html>')


def _table_html(t):
    rows = "".join(
        f'<tr><td>{_esc(r["label"])}</td>'
        f'<td class="r">{r["required"]}</td>'
        f'<td class="r">{r["margin"]:+d}</td>'
        f'<td class="r">{r["ratio"]}&times;</td>'
        f'<td class="r">{_badge(r["badge"])}</td></tr>'
        for r in t["rows"])
    return (f'<div class="sub-header">{_esc(t["title"])} &middot; xw {t["crosswind"]} kt '
            f'{_badge(t["crosswind_badge"])}</div>'
            f'<table><thead><tr><th></th><th class="r">Req’d</th>'
            f'<th class="r">Margin</th><th class="r">Ratio</th><th class="r"></th></tr></thead>'
            f'<tbody>{rows}</tbody></table>')


def _block_html(blk):
    tables = "".join(_table_html(t) for t in blk["tables"]) or \
        '<div class="remark">No usable runways found.</div>'
    s = blk["speeds"]
    if blk["phase"] == "takeoff":
        speeds = (f'<div class="sub-header">Stall / Climb</div>'
                  f'<div class="speeds"><span>Vs: <b>{s["vs_clean"]}</b> cln '
                  f'<b>{s["vs_15"]}</b> 15&deg; <b>{s["vs_full"]}</b> full</span></div>'
                  f'<div class="speeds"><span>Vx <b>{s["vx"]}</b> &nbsp; Vy <b>{s["vy"]}</b> '
                  f'&nbsp; ROC <b>{s["roc"]}</b> fpm</span></div>')
    else:
        speeds = (f'<div class="sub-header">Stall / Approach</div>'
                  f'<div class="speeds"><span>Vs: <b>{s["vs_clean"]}</b> cln '
                  f'<b>{s["vs_15"]}</b> 15&deg; <b>{s["vs_full"]}</b> full</span>'
                  f'<span style="margin-left:auto">Vapp: <b class="highlight">{s["vapp"]} kt</b>'
                  f'</span></div>')
    remarks = "".join(f'<div class="remark">{_esc(r)}</div>' for r in blk["remarks"])
    priv = ' <span class="rwy-info">(private)</span>' if blk.get("private") else ""
    return (f'<div class="airport">'
            f'<div class="apt-header">{_esc(blk["id"])} &mdash; {_esc(blk["name"])}{priv} '
            f'<span class="rwy-info">{_esc(blk["runways_label"])}</span></div>'
            f'<div class="apt-meta"><b>{blk["temp_f"]}&deg;F</b> &nbsp; PA <b>{blk["pa"]}</b> '
            f'&nbsp; DA <b>{blk["da"]}</b> ft &nbsp;|&nbsp; Wind <b>{_esc(blk["wind_label"])}</b></div>'
            f'{tables}{speeds}{remarks}</div>')


def render_html(sheet):
    summary = "".join(
        f'<div><div class="label">{_esc(s["label"])}</div>'
        f'<div class="val {"warn" if s["badge"] == "warn" else ""}">{_esc(s["val"])}</div></div>'
        for s in sheet["summary"])
    age = sheet.get("metar_age", {})
    age_str = ", ".join(f'{k} {v}min' for k, v in age.items() if v is not None)
    body = (
        f'<div class="top-bar"><div><h1>{_esc(sheet["tail"])}</h1>'
        f'<span class="route">{_esc(sheet["route"])}</span></div>'
        f'<div class="top-params">TO <b>{sheet["to_weight"]}</b> lb &nbsp;|&nbsp; '
        f'LDG <b>{sheet["ldg_weight"]}</b> lb &nbsp;|&nbsp; Fuel <b>{sheet["fuel_gal"]}</b> gal '
        f'&nbsp;|&nbsp; Burn <b>~{sheet["burn_gal"]}</b> gal &nbsp;|&nbsp; {sheet["dist_nm"]} nm '
        f'&nbsp;|&nbsp; {_esc(sheet["power"])} {sheet["rpm"]} {_esc(sheet["mixture"])}</div></div>'
        f'<div class="warnbar">Experimental &mdash; digitized POH approximation, not flight-tested. '
        f'Verify against the POH.</div>'
        f'<div class="actions"><a href="/">&larr; New plan</a>'
        f'<button onclick="window.print()">Print / Save PDF</button></div>'
        f'<div class="cols">{_block_html(sheet["dep"])}{_block_html(sheet["dest"])}</div>'
        f'<div class="summary">{summary}</div>'
        f'<div class="notes">{_esc(sheet["notes"])} &nbsp; Generated {_esc(sheet["generated"])}'
        + (f' &nbsp; METAR age: {_esc(age_str)}.' if age_str else "")
        + (f' &nbsp; Airport data: {_esc(sheet.get("data_built"))}' if sheet.get("data_built") else "")
        + '</div>')
    return _page(f'{sheet["tail"]} Safety — {sheet["route"]}', body)


_FORM_CSS = """
* { box-sizing: border-box; } body { font-family: -apple-system, 'Helvetica Neue', Arial, sans-serif;
  max-width: 460px; margin: 0 auto; padding: 18px; color: #111; }
h1 { font-size: 20px; margin-bottom: 2px; } .sub { color: #666; font-size: 13px; margin-bottom: 16px; }
label { display: block; font-size: 13px; font-weight: 600; margin: 12px 0 4px; }
input, select { width: 100%; padding: 11px; font-size: 16px; border: 1px solid #bbb; border-radius: 8px; }
.row { display: flex; gap: 10px; } .row > div { flex: 1; }
button { width: 100%; margin-top: 18px; padding: 14px; font-size: 17px; font-weight: 700;
  background: #0a4; color: #fff; border: none; border-radius: 8px; }
details { margin-top: 14px; } summary { font-size: 13px; font-weight: 600; cursor: pointer; }
.err { background: #fdd; border: 1px solid #c44; border-radius: 8px; padding: 10px; margin-bottom: 14px; font-size: 14px; }
.note { color: #888; font-size: 11px; margin-top: 18px; line-height: 1.4; }
"""


def _field(label, name, params, default="", typ="text", placeholder="", **attrs):
    val = _esc(params.get(name, default))
    extra = " ".join(f'{k}="{v}"' for k, v in attrs.items())
    return (f'<label>{_esc(label)}</label>'
            f'<input name="{name}" type="{typ}" value="{val}" '
            f'placeholder="{_esc(placeholder)}" {extra}>')


def form_html(params, error=None):
    err = f'<div class="err">{_esc(error)}</div>' if error else ""
    mix = params.get("mixture", "best_economy")
    body = f"""<style>{_FORM_CSS}</style>
<h1>N9082P Safety Sheet</h1>
<div class="sub">Takeoff &amp; landing performance from POH charts + live FAA weather.</div>
{err}
<form method="get" action="/">
  <div class="row">
    <div>{_field("Departure", "dep", params, placeholder="S95", autocapitalize="characters", autocomplete="off", required="required")}</div>
    <div>{_field("Destination", "dest", params, placeholder="S33", autocapitalize="characters", autocomplete="off", required="required")}</div>
  </div>
  <div class="row">
    <div>{_field("Takeoff weight (lb)", "weight", params, "2700", "number", min="1900", max="3100")}</div>
    <div>{_field("Fuel (gal)", "fuel", params, "86", "number", min="0", max="90")}</div>
  </div>
  <details>
    <summary>Advanced (cruise &amp; overrides)</summary>
    <div class="row">
      <div>{_field("Cruise alt (ft)", "cruise_alt", params, "7500", "number")}</div>
      <div>{_field("Power (%)", "power", params, "65", "number", min="45", max="75")}</div>
    </div>
    <div class="row">
      <div>{_field("RPM", "rpm", params, "2400", "number")}</div>
      <div>
        <label>Mixture</label>
        <select name="mixture">
          <option value="best_economy"{" selected" if mix == "best_economy" else ""}>Best economy</option>
          <option value="best_power"{" selected" if mix == "best_power" else ""}>Best power</option>
        </select>
      </div>
    </div>
    {_field("Landing weight override (lb)", "landing_weight", params, "", "number", placeholder="auto")}
  </details>
  <button type="submit">Generate safety sheet</button>
</form>
<div class="note">Experimental: performance from digitized POH Section 5 charts (5% conservative bias),
not flight-tested. Airport data: FAA AIS. Weather: NOAA/NWS. Always verify against the POH.</div>"""
    return _page("N9082P Flight Planner", body)


def error_html(message, params):
    return form_html(params, error=message)


def login_html(error=None, next_url="/"):
    err = f'<div class="err">{_esc(error)}</div>' if error else ""
    body = f"""<style>{_FORM_CSS}</style>
<h1>N9082P</h1>
<div class="sub">Enter the password to open the flight planner.</div>
{err}
<form method="post" action="/login">
  <input type="hidden" name="next" value="{_esc(next_url)}">
  <label>Password</label>
  <input name="password" type="password" autocomplete="current-password" autofocus required>
  <button type="submit">Sign in</button>
</form>
<div class="note">Private tool for N9082P. You'll stay signed in on this device for 30 days.</div>"""
    return _page("N9082P — Sign in", body)

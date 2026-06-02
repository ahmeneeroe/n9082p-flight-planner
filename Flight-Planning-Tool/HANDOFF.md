# N9082P Flight Planner — EXHAUSTIVE HANDOFF (snapshot 2026-05-30)

Read this first if you're a new session. It consolidates architecture, AWS inventory, the
card's layout/rendering, every performance/data finding, decisions, gotchas, and commands.
Canonical companions: `README.md` (ops), `research.md` (deep build log), `../speeds.md` &
`../POH.md` (POH digests, at the N9082P root — NOT in the public repo), and the code itself.

---

## 0. TL;DR / current state

- **Live:** https://flight-planning.davidameneyro.com  (custom domain) — password-gated.
  Raw origin (always works): `https://nvnl7kstmkaw7f7iyvjxwayx440fakjq.lambda-url.us-west-2.on.aws/`
- **Login password:** set via the `PLANNER_PASSWORD` Lambda env var; owner intentionally keeps the current value (see §11). DO NOT re-flag or change without asking.
- **What it is:** a mobile web app → a print-ready **A5 landscape preflight safety sheet** for N9082P
  (1966 Piper PA-24-260B Comanche): per-runway takeoff/landing margins, density altitude, wind
  components, stall/approach speeds, best glide, destination climb rate, OK/CAU/WARN badges.
- **Data:** FAA-authoritative airports (FAA AIS) + live NWS METAR + digitized POH performance calculator.
- **Repo (PUBLIC):** https://github.com/ahmeneeroe/n9082p-flight-planner
- **Resume:** `cd /Users/papillonm5/Documents/Flying/N9082P/Flight-Planning-Tool && claude --resume N9082P-Perfomance-Online`
- **Status: COMPLETE.** No pending work. (Optional ideas only; see §11.)

---

## 1. Where things live (working copy vs. published repo)

- **Working / deploy source:** `~/Documents/Flying/N9082P/Flight-Planning-Tool` with the **sibling
  `../Performance`** calculator. A new session resumes HERE. Deploy from here.
- **Public repo export:** `~/Documents/Flying/n9082p-flight-planner` (separate dir holding the `.git`).
  It's a *clean export* — account ID genericized to `<AWS_ACCOUNT_ID>`, and POH chart scans / PDFs /
  `.claude` / build junk excluded. After changing the working copy, re-sync (see §10).
- **NOT in the repo / not in the app bundle:** `../speeds.md`, `../POH.md`, and the rest of the
  N9082P private docs (logbooks, insurance, transaction). They stay local under `~/Documents/Flying/N9082P/`.

## 2. Code layout (`Flight-Planning-Tool/`)

```
planner/
  __init__.py
  data.py        # load airport bundle: S3 (DATA_BUCKET) w/ bundled fallback; logs [data] source=...
  weather.py     # NWS METAR fetch + nearest-station (bbox) + parse (C->F, hPa->inHg)
  geo.py         # haversine, initial_bearing, wind_components, pressure_altitude, density_altitude, std temp
  safety.py      # OK/CAU/WARN thresholds: runway ratio, crosswind (17 kt demo), DA, weight
  generate.py    # build_sheet(): orchestrates everything -> a "sheet" dict
  render.py      # render_html(sheet) -> A5 HTML; also form_html / login_html / error_html
  perf.py        # bridge to the calculator: bundled `perf_engine` (Lambda) or sibling ../Performance/src (local)
app/
  handler.py     # framework-agnostic handle() + lambda_handler (Function URL payload v2.0); cookie auth
  devserver.py   # local http.server mirroring the Lambda (python3 app/devserver.py -> localhost:8000)
tools/build_faa_airports.py   # build data/airports_faa.json from FAA AIS (stdlib; also runs as the refresher)
refresh/refresh_handler.py    # refresher Lambda handler: build + upload to S3
deploy/build.sh        # zip the app (Performance/src copied in as perf_engine)
deploy/deploy.sh       # create/update app Lambda + Function URL + 2 invoke perms + role S3-read + env
deploy/deploy_refresh.sh  # refresher Lambda + role + EventBridge 28-day schedule
deploy/deploy_alerts.sh   # SNS topic + email sub + CloudWatch errors alarm
data/airports_faa.json    # bundled FAA airport data (fallback baseline; ~12,846 US airports)
files/                    # sample A5 HTML (prototypes); PDFs here are .gitignored
README.md, HANDOFF.md, design.md, research.md, todo.md
```
Sibling `../Performance/`: the calculator (`src/calculator.py` = `N9082P` class; `src/models/*` one per
POH Sec 5 figure; `src/utils/` atmosphere/interpolation/units; `tests/test_validation.py`;
`charts/data/*.json` digitized points; `charts/*.png` POH scans — excluded from repo).

**Pure Python standard library** — no third-party deps; deploys as a plain zip. `boto3` comes from the
Lambda runtime (used by the app's S3 read and the refresher's S3 upload; guarded so local dev needs no boto3).

## 3. Request flow

```
Browser -> CloudFront (custom domain, HTTPS) -> Lambda Function URL -> app/handler.lambda_handler
        -> handle(): cookie auth gate -> planner.generate.build_sheet() -> planner.render.render_html() -> A5 HTML
```
- **Auth:** password -> HMAC-signed cookie (`n9082p_auth`, 30-day, Secure/HttpOnly/SameSite=Lax).
  POST `/login` checks password vs `PLANNER_PASSWORD`, sets cookie, 302 to `/`. NOT HTTP Basic Auth —
  Lambda Function URLs **remap** `WWW-Authenticate` to `x-amzn-Remapped-www-authenticate`, so the browser
  dialog never appears. Cookie value goes in the Function URL response `cookies` array (not headers).
- **Inputs (GET query):** dep, dest, weight (TO lb), fuel (gal); advanced: cruise_alt, power, rpm,
  mixture, landing_weight override. Weather auto (METAR), nearest station for non-reporting fields.

## 4. AWS inventory (account `<AWS_ACCOUNT_ID>`, `us-west-2` unless noted)

| Resource | Name / value |
|---|---|
| App Lambda | `n9082p-planner`; handler `handler.lambda_handler`; env `PLANNER_PASSWORD`, `DATA_BUCKET`, `DATA_KEY`; role `n9082p-planner-role` |
| Function URL | AuthType **NONE**; resource policy needs **BOTH** `lambda:InvokeFunctionUrl` AND `lambda:InvokeFunction` (Oct-2025 rule) |
| Edge / domain | CloudFront `ESYJH857V9VMT` (`d1g4lk8265qufv.cloudfront.net`) — CachingDisabled + AllViewerExceptHostHeader (forwards cookies + query strings) |
| TLS cert | ACM **us-east-1** `e50c5b65-b203-48b5-8830-92a711b4a7ae` for flight-planning.davidameneyro.com |
| Data bucket | S3 `n9082p-planner-data-<AWS_ACCOUNT_ID>` (private) — live `airports_faa.json` |
| Refresher | Lambda `n9082p-data-refresh` + role `n9082p-data-refresh-role`; EventBridge rule `n9082p-data-refresh-28d` = `rate(28 days)` |
| Alerting | SNS `n9082p-alerts` (email David.ameneyro@gmail.com — **confirmed + test-fired**); CloudWatch alarm `n9082p-data-refresh-errors` |
| DNS | Namecheap **BasicDNS**: `flight-planning` CNAME -> CloudFront + the ACM validation CNAME. (Edit in Namecheap Advanced DNS, NOT Route 53.) |

## 5. Data pipeline (self-maintaining)

- **Source:** FAA AIS (ArcGIS, org `AeronauticalInformationServices_FAA`): `US_Airport/FeatureServer/0`
  + `Runways/FeatureServer/0`. See the `faa-data` skill for schema/gotchas (DMS lat/lon, IDENT/ICAO
  aliasing, helipad/closed-runway filtering, runway heading from designator). Elevation already in feet.
- **Refresh:** EventBridge fires `n9082p-data-refresh` every 28 days -> `tools/build_faa_airports.py`
  rebuilds the JSON (stamps `_meta.built` UTC) -> uploads to S3. The app (`planner/data.py`) reads S3
  per cold start (cached /tmp + module mem), falls back to the bundled file on any S3 failure -> never hard-fails.
- **Monitoring:** failed refresh -> CloudWatch `errors` alarm -> SNS email. (No active "no-run" alarm —
  CloudWatch caps alarm windows at 1 week, can't express 28-day; **staleness is shown passively** as
  "Airport data: <date>" on every sheet, from `_meta.built`.)
- **Weather:** NWS aviationweather.gov METAR (temp C->F, altim hPa->inHg, wind true). S95 has no METAR ->
  nearest station via bbox (e.g. KALW).

## 6. The A5 card — layout & rendering (`planner/render.py`)

Pure string templating; A5 **landscape, black & white**, print-ready (`@page { size: A5 landscape }`),
responsive to single-column under 760px screen. Regions, top to bottom:

1. **Top bar:** `N9082P` + route (e.g. `S95 → S33`) on the left; on the right a params line:
   `TO <w> lb | LDG <w> lb | Fuel <g> gal | Burn ~<g> gal | <dist> nm | <power> <rpm> <mixture> | Best glide <kt> kt @<wt> lb (est)`.
2. **Warn bar:** boxed "Experimental — digitized POH approximation, not flight-tested. Verify against the POH."
3. **Actions** (screen only, hidden in print): "← New plan", "Print / Save PDF".
4. **Two columns** (`.cols`, dep | dest), each an `.airport` block:
   - **Header:** `IDENT — Name (private?)` + runway list (`05/23: 3819 | ...`, longest 3).
   - **Meta:** `<temp>°F  PA <pa>  DA <da> ft | Wind <label>`.
   - **Per-runway tables** (favored end of up to 3 longest runways, picked by max headwind): 4 rows —
     SF ground run/roll, SF over 50 ft, Std ground run/roll, Std over 50 ft — columns Req'd / Margin /
     Ratio / badge. Sub-header carries the runway, wind phrase, crosswind + xw badge.
     `Std = 2× short-field`; `limiting_ratio` = available / (SF over-50 × 2).
   - **Speeds:**
     - Departure block (`phase="takeoff"`): "Stall / Climb" — Vs cln/15°/full; Vx, Vy, ROC fpm (TO weight).
     - Destination block (`phase="landing"`): "Stall / Approach / Climb" — Vs cln/15°/full; **Vapp** (highlighted);
       and **"Climb (landing wt @ field DA): ROC <fpm>  Vy <kt>"** (NEW — clean best-rate climb at the
       destination's field DA and the landing weight; go-around / climb-out margin).
   - **Remarks:** runway surface/lighting; WX source/station+distance, or "no METAR — std day assumed".
5. **Summary strip** (`.summary` auto-fit grid): TO Wt, LDG Wt, DA dep, DA dest, then each runway's
   limiting ratio. WARN cells underlined.
6. **Notes footer:** the EXPERIMENTAL provenance line (digitized POH Sec 5, 5% bias, Std=2×SF, wind =
   runway-number vs METAR, best-glide & dest-climb provenance) + `Generated <UTC>` + METAR age + `Airport data: <built date>`.

`safety.py` badges: runway ratio OK≥2.0 / CAU 1.5–2.0 / WARN<1.5; crosswind OK<12 / CAU≤17 (demo) / WARN>17;
DA OK<5000 / CAU≤8000 / WARN>8000; weight WARN over limit.

## 7. Performance calculator (`../Performance`) — EXPERIMENTAL

`N9082P` class: `takeoff, landing, climb, cruise, stall, power_setting, summary` (all return dicts).
14 POH **Section 5** charts digitized via WebPlotDigitizer; **5% conservative bias** on takeoff/landing
(nomogram compounding). **HARD RULE (owner's `feedback_performance_separation`): digitized data is NOT
POH-authoritative — never present it as "per POH"; keep it separate; keep the EXPERIMENTAL banner.**
Stall speed scales `V = V_ref·√(W/3100)` (lift eqn). Units: POH is MPH; present in **knots**. See the
`poh-digitization` skill.

## 8. Best glide (added 2026-05-30) — findings, method, sourcing

- **POH source (verbatim):** Section 3 (Emergency Procedures), **p3-2** "Engine Power Loss During Flight":
  *"Airspeed … Establish Best Glide (105 mph or 91 kt @ Full Gross Weight)"* with **NOTE: "Best engine-out
  glide speed decreases as the airplane's gross weight decreases."* Repeated **p3-5** "Power Off Landing".
- **KEY FINDING:** the POH gives the weight note **only qualitatively — NO RATE.** The "~1 kt per 100 lb"
  rule (and the ~86/~82 table) that *was* in `speeds.md` was a **digest extrapolation, NOT the POH** —
  corrected. (This is exactly why the owner asked "where in the POH is this?" — good catch.)
- **Method (chosen):** best-L/D speed ∝ √weight, so scale the POH gross value:
  `best_glide_kt = round(91 · √(min(W,3100)/3100))`, evaluated at the **mid-flight weight**
  `(takeoff_weight + landing_weight)/2`. Implemented in `generate.py::_best_glide_kt`. Labeled **"(est)"** on
  the card; it is a **derived estimate, NOT POH**.
- **Why √ over linear:** physics (fixed-CL speed) + corroboration — the owner's **commercial checklist gives
  73 kt @ 2000 lb, which equals 91·√(2000/3100)=73** exactly. The old linear rule gave 80 there (wrong).
  Recorded in `../speeds.md` "Best Glide vs Weight".
- **Example:** S95→S33, midway 2581 lb → **83 kt**. Shown top-bar: "Best glide 83 kt @2581 lb (est)".

## 9. Destination climb rate (added 2026-05-30)

`generate.py::_airport_block` (landing branch) calls `calc.climb(dest_pa, dest_oat, weight_lb=landing_weight)`
→ adds `roc` + `vy` to the dest speeds. Uses the **destination's live METAR** (PA/DA) and the **landing
weight**, clean config (best-rate). Rendered as "Climb (landing wt @ field DA): ROC <fpm>  Vy <kt>" in the
dest block. Purpose: go-around / climb-out margin at the destination's density altitude (matters at high-DA
fields — e.g. S33 showed DA ~3800 ft on a warm day, ROC ~1480 fpm at ~2536 lb).

## 10. Common tasks (run `aws sso login` first — SSO expires ~4h, and a RESUMED session almost always needs it)

- **Local dev:** `python3 app/devserver.py` → http://localhost:8000/ (open, no password; uses bundled data).
- **Redeploy app:** `PLANNER_PASSWORD=<password> bash deploy/deploy.sh` (rebuilds zip from generate/render/etc.,
  sets env incl. DATA_BUCKET, ensures S3-read role policy + both Function-URL invoke perms).
- **Refresher / schedule:** `bash deploy/deploy_refresh.sh`. **Force a refresh now:**
  `aws lambda invoke --function-name n9082p-data-refresh --region us-west-2 /tmp/r.json`.
- **Alerts:** `bash deploy/deploy_alerts.sh [email]`.
- **App logs / data source:** `aws logs tail /aws/lambda/n9082p-planner --since 1h --region us-west-2` (find `[data] source=...`).
- **Live verify pattern:** `curl -s -c /tmp/cj -d "password=<pw>&next=/" "<url>"` then `curl -s -b /tmp/cj "<url>?dep=S95&dest=S33&weight=2627&fuel=90"`.
- **Re-sync the public repo** (git push needs only `gh` auth, NOT AWS SSO):
  ```
  REPO=~/Documents/Flying/n9082p-flight-planner ; SRC=~/Documents/Flying/N9082P
  rm -rf "$REPO/Flight-Planning-Tool" "$REPO/Performance"
  for d in Flight-Planning-Tool Performance; do rsync -a \
    --exclude=__pycache__ --exclude='*.pyc' --exclude=.DS_Store --exclude=.venv --exclude='*.zip' \
    --exclude=build --exclude=build-refresh --exclude=.claude --exclude='*.png' --exclude='*.pdf' \
    "$SRC/$d" "$REPO/"; done
  find "$REPO" -type f \( -name '*.md' -o -name '*.sh' \) -print0 | xargs -0 sed -i '' 's/<AWS_ACCOUNT_ID>/<AWS_ACCOUNT_ID>/g'
  # VERIFY: no forbidden files, no raw account ID, no AWS keys, no committed login password, THEN:
  git -C "$REPO" add -A && git -C "$REPO" commit -m "..." && git -C "$REPO" push origin main
  ```

## 11. Decisions & non-issues (do NOT re-litigate)

- **Login password:** owner explicitly keeps the current value as-is despite the public repo — accepts it's guessable; **don't re-flag or change without asking.** (The value lives only in the Lambda `PLANNER_PASSWORD` env var, never in the repo.)
- **Repo is PUBLIC** (owner's choice) — hence the account-ID genericization + secret scans on every push.
- **Best glide weight method = √weight, labeled est** (see §8). Not POH; corroborated by the checklist.
- **No active "data is stale" alarm** — CloudWatch 1-week window cap; on-sheet build-date covers it.
- **Optional future ideas only (none requested):** rotate password; richer per-runway obstacle data; more
  airports' nearest-METAR mapping tuning.

## 12. Gotchas / lessons (consolidated — all already handled)

1. **403 on the public Function URL was NOT an org policy.** Since **Oct 2025** a NONE Function URL needs
   BOTH `lambda:InvokeFunctionUrl` AND `lambda:InvokeFunction` in the resource policy; missing the 2nd = 403.
   The org has only the default `FullAWSAccess` SCP; RCPs don't even cover Lambda.
2. **Basic Auth doesn't work via Function URLs** — `WWW-Authenticate` gets remapped to `x-amzn-Remapped-*`.
   → cookie login.
3. **Custom domain** needs CloudFront (Function URLs can't take one directly) + ACM cert in **us-east-1**.
   Subdomain ≫ apex (apex already serves an S3 site).
4. **zsh doesn't word-split unquoted vars** — pass rsync `--exclude=...` flags inline/quoted, not via `$VAR`.
5. **SSO expires ~4h / on resume** — `aws sso login` (browser, sign in as `papillon`). git push is unaffected.
6. **FAA AIS** (not OurAirports, not the aviationweather *airport* API, not NASR-bulk which 503s here). See `faa-data` skill.
7. **`speeds.md`/`POH.md` are digests** — verify against the actual POH PDFs in `../Manuals/Sections/POH-Sec*.pdf`
   before treating a digest annotation as authoritative (the best-glide rate error is the cautionary tale).

## 13. Skills & global config (in `~/.claude/`)

Skills: **`faa-data`**, **`poh-digitization`**, **`md-to-html`** (new), **`aws-cli`** (updated w/ the Lambda-web-app
section). `CLAUDE.md` has a **Domains / DNS** section. Apple Notes "Claude" folder has a project note +
"CLAUDE.md (current)". Auto-memory: `flight_planning_web_app_deployed.md`, `reference_domain_dns.md` (+ MEMORY.md index).

# Flight Planning Tool — Web App Build (todo)

**Goal:** Mobile web page on AWS where I enter departure / destination / takeoff weight /
fuel and get back the A5 safety sheet. Build & test locally now; deploy once AWS CLI is
configured.

## Decisions (locked 2026-05-29)
- **Hosting:** AWS Lambda + Function URL — serverless, ~$0/mo, pure-stdlib zip deploy (calculator has zero 3rd-party deps)
- **Access:** password-protected via HTTP Basic Auth; password stored in Lambda env var (never in code)
- **AWS account:** CONFIGURED — AWS CLI v2 via IAM Identity Center SSO; account <AWS_ACCOUNT_ID>, default profile, AdministratorAccess. `aws sso login` if token expired (~4h). No long-lived keys. (See aws-cli skill.)
- **Region:** us-west-2 (Oregon — closest to PNW) — confirmed (matches AWS default)
- **Airport data:** FAA AIS (AeronauticalInformationServices_FAA ArcGIS) = authoritative FAA charting data. Bundled to data/airports_faa.json via tools/build_faa_airports.py; refresh monthly (FAA 28-day cycle) + redeploy. NASR = same FAA data but nfdc.faa.gov blocks automated fetch here. OurAirports REJECTED (community-sourced). Validated: S95 05/23 3819ft matches hand-read Chart Supplement.
- **METAR:** aviationweather.gov = NOAA/NWS Aviation Weather Center (US govt authoritative; FAA points pilots here). Unchanged.

## STATUS — 2026-05-30: ENGINE + APP BUILT & TESTED LOCALLY ✅
- ✅ FAA airport bundle: data/airports_faa.json (12,846 US airports, 0 skipped, helipads filtered) via tools/build_faa_airports.py
- ✅ planner/: data, geo (haversine/wind/PA/DA), weather (NWS METAR + nearest-station), safety, generate, render (A5 HTML)
- ✅ app/: handler.py (Lambda + Basic Auth) + devserver.py (local). Shared core.
- ✅ Validated vs prototype (S95→S33): Rwy 23 8hw; S33 Rwy04 1.0× WARN; Vs/Vx/Vy/Vapp; DA. Sample: files/sample-S95-S33-live.html
- ✅ Tests pass: form / plan / bad-airport / Basic Auth (401·200·401); bundle runs self-contained
- ✅ deploy/build.sh (zip) + deploy/deploy.sh (Lambda + Function URL, us-west-2) written
- ✅ DEPLOYED & LIVE: **https://flight-planning.davidameneyro.com** (CloudFront + custom domain, ACM cert) and the raw Lambda Function URL. Signed-cookie login.
- ✅ Fixed: Oct-2025 dual-permission 403 (added lambda:InvokeFunction); WWW-Authenticate remap (Basic Auth → cookie login).
- ✅ WRAP-UP: README + memory updated; session named N9082P-Perfomance-Online.
- ⏳ OPTIONAL NEXT: automate monthly FAA data refresh (EventBridge); rotate password off the tail number.
- ⏳ FOLLOW-UP (requested 2026-05-30): **add this project to GitHub** (`gh repo create` + push; gh is authed as ahmeneeroe over HTTPS). Decide public vs private and whether to include data/airports_faa.json (5.9 MB) or .gitignore it + document the build step.
- **Safety:** A5 must carry an "EXPERIMENTAL — verify against POH" banner (digitized chart data, 5% bias, unvalidated). See memory `feedback_performance_separation`.
- **v1 inputs:** departure, destination, takeoff weight, fuel (gal). Weather = auto METAR. Everything else defaults (65% power, 2400 RPM, best economy, standard 2x technique).

## Phase 0 — Ground truth (investigation)  ✅ DONE (see research.md)
- [x] Probe airport API — elev in METERS; runway id/dimension/surface/alignment. **API does NOT return S95/S33/7S3** (only ICAO/towered fields) → need OurAirports or hand-seeded data.
- [x] Probe METAR API — temp °C, altim hPa, wdir/wspd. S95→KALW mapping confirmed.
- [x] A5 prototype is pure HTML+CSS (no JS/graphics) → output is cheap string templating, NOT the hard part.
- [x] calculator.py API mapped (takeoff/landing/climb/cruise/stall/summary; takeoff/landing take headwind_kt scalar → wind math is ours).

**Key reframe:** output format is cheap; the real v1/v2 fork is AIRPORT DATA coverage (decision pending with owner).

## Phase 1 — Generator (the missing engine)
- [ ] planner/airport.py — load bundled FAA AIS data (data/airports_faa.json), resolve by IDENT/ICAO, expose elevation + runways. Source = FAA AIS (authoritative). Bundle built by tools/build_faa_airports.py.
- [ ] planner/weather.py — METAR fetch + parse; compute PA / DA / wind components
- [ ] planner/route.py — haversine distance, magnetic course, wind decomposition
- [ ] planner/safety.py — runway-margin / crosswind / DA / weight checks (OK/CAU/WARN)
- [ ] planner/render.py — A5 HTML renderer (matches prototype + experimental banner)
- [ ] planner/generate.py — orchestrate: inputs → data → calc → A5 HTML

## Phase 2 — Web wrapper
- [ ] app/handler.py — Lambda handler: GET / (form), POST /generate (A5), Basic Auth gate
- [ ] app/form.html — mobile input form (dep, dest, weight, fuel + optional collapsible)
- [ ] app/devserver.py — local http.server adapter (test on this Mac, no AWS needed)

## Phase 3 — Local test
- [ ] Run devserver; generate S95→S33 sheet; compare to prototype + ForeFlight navlog
- [ ] Verify Basic Auth gate works

## Phase 4 — Deploy (when AWS CLI ready)
- [ ] deploy/build.sh — zip Performance/src + planner + app
- [ ] deploy/deploy.sh — create/update Lambda, Function URL, set password env var, region
- [ ] Smoke test from phone; bookmark / add to home screen
- [ ] Update README + Apple Note + resume command

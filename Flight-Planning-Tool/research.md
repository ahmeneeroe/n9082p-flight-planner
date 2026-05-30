# Build Research Log — Flight Planning Web App

## 2026-05-29 — Phase 0 ground-truth (code + live APIs + A5 layout)

### Code state (verified)
- `Performance/src/calculator.py`: **pure stdlib, ZERO third-party deps** → trivial Lambda zip, no layers/containers.
- **No HTML generator anywhere.** The `files/*.html` A5 sheets were hand-built artifacts, not program output. Reproducing them dynamically is the work to do.
- `calculator.N9082P` API (all return dicts):
  - `takeoff(pressure_alt_ft, oat_f, weight_lb, headwind_kt, surface="paved_dry", uphill_deg)` → `ground_run_ft` (short field), `over_50ft_obstacle_ft`, `ground_run_standard_ft` (=2×), `vso_kt`, `density_altitude_ft`
  - `landing(pressure_alt_ft, oat_f, weight_lb, headwind_kt, surface, downhill_deg)` → `ground_roll_ft`, `over_50ft_obstacle_ft`, `ground_roll_standard_ft` (=2×), `approach_speed_kt`, `density_altitude_ft`
  - `climb(pressure_alt_ft, oat_f, target_alt_ft, config, weight_lb)` → `rate_of_climb_fpm`, `vx_kt`, `vy_kt`, `fuel_flow_climb_gph`, (+time/fuel-to-climb if target set)
  - `cruise(...)`, `stall(weight_lb)` → clean/15°/full-flap stall + approach kt, `summary(...)`
  - **takeoff/landing take `headwind_kt` (scalar)** — wind-component math (head/cross from wind dir + runway heading) is OUR job upstream.

### aviationweather.gov AIRPORT API  `?ids=...&format=json`
- **`elev` is in METERS** (KALW 364→1194 ft, KBOI 875→2871 ft; ×3.281).
- `runways`: `[{id:"02/20", dimension:"6527x150", surface:"C", alignment:36}]` (surface C=concrete, A=asphalt; alignment ≈ true heading of lower-numbered end).
- Other fields: id, icaoId, faaId, iataId, name, elev, lat, lon, magdec, freqs, runways, rwyNum.
- **SHOWSTOPPER:** queried `S95, S33, 7S3, KALW, KBOI` → only **KALW & KBOI** returned. API does **not** resolve small/FAA-only identifiers (S95, S33, 7S3 — the fields the owner actually flies). Also returned only **1 of KALW's 3 runways**. → need a different airport/runway source.
  - Candidates: **OurAirports CSV** (has all US fields incl. private/turf, with runway le/he ident, length, width, surface, true heading, end elevation) or hand-curated JSON for owner's airports.

### aviationweather.gov METAR API  `?ids=...&format=json`
- `temp`/`dewp` in **°C** (→°F for calculator). `altim` in **hPa/mb** (KALW 1016 = A3000 = 30.00 inHg; inHg = hPa×0.02953). `wdir`°, `wspd` kt, `wgst`, `rawOb`.
- Keyed by ICAO. Non-reporting fields (S95/S33/7S3) → nearest station (S95→KALW confirmed, 5.7 NM same valley). General approach: bbox around field lat/lon, pick nearest recent ob.

### A5 layout (`files/safety-sheet-S95-S33-a5-bw.html`)
- Pure HTML+CSS, **no JS, no images**. A5 landscape, 2-col (dep | dest), per-runway TO/LDG tables (Req'd / Margin / Ratio / badge OK·CAU·WARN), stall/climb speeds, summary strip, disclaimer note already present.
- → Reproducing it is **simple string templating**. Output format is the cheap part; data plumbing is the work.

### Implications for v1 scope
- **A5 output is near-free** (prototype = the template). Downgrading output saves little.
- **Real v1/v2 fork is airport data:** general (OurAirports, any US field) vs hand-seeded (owner's airports only). ← decision pending with owner.
- Conversions to handle: airport elev m→ft, METAR temp °C→°F, altim hPa→inHg, PA from altimeter, wind→head/cross components.

## 2026-05-29 (later) — DATA PROVENANCE LOCKED: FAA-authoritative (owner requested extreme FAA bias)

Owner requirement: airport AND METAR data must be FAA-authoritative; a monthly cron is acceptable.

- **OurAirports REJECTED** — community DB, FAA-derived but not authoritative. (Prior session actually used FAA Chart Supplement A/FD pages — files/nw_187, nw_228 — so OurAirports would have *regressed* provenance. Builder tools/build_airport_data.py deleted.)
- **METAR = aviationweather.gov** — NOAA/NWS Aviation Weather Center, the US-government authoritative aviation weather source (FAA directs pilots here). Honest nuance: NWS, not literally FAA, but there is no more authoritative govt METAR. Unchanged from prior session.
- **Airport data = FAA AIS** (org `AeronauticalInformationServices_FAA` ArcGIS open data; backed by FAA ADIP):
  - Airports: `services6.arcgis.com/ssFJjBXIUyZDrSYZ/.../US_Airport/FeatureServer/0`
  - Runways : `services6.arcgis.com/ssFJjBXIUyZDrSYZ/.../Runways/FeatureServer/0`
  - Airport fields: IDENT, ICAO_ID, NAME, ELEVATION (ft), LATITUDE/LONGITUDE (DMS strings), TYPE_CODE (AD=airport), OPERSTATUS, PRIVATEUSE, GLOBAL_ID.
  - Runway fields: AIRPORT_ID (→ airport GLOBAL_ID), DESIGNATOR ("05/23"), LENGTH, WIDTH, COMP_CODE (surface). No heading field → derive from DESIGNATOR digits ×10. Geometry not needed (returnGeometry=false).
  - Join runways→airport by `AIRPORT_ID == airport GLOBAL_ID` (two-step: airport by IDENT → GLOBAL_ID → runways).
  - **VALIDATED**: S95/S33/7S3/ALW(KALW)/BOI(KBOI) all resolve by IDENT. S95 = "Martin Fld" elev 750, rwy 05/23 3819×60 ASPH — EXACTLY matches the prototype's hand-read Chart Supplement value → provenance proven equivalent. elev already in FEET (no conversion). lat/lon DMS → parse to decimal.
- **NASR 28-day subscription** (nfdc.faa.gov) = same underlying FAA data, but the host returns **503 to automated fetch from this environment** (bot/WAF/flaky), even with a browser UA. The per-edition download page (www.faa.gov/.../NASR_Subscription/2026-05-14) is 403 to WebFetch. Current cycle effective 2026-05-14, next 2026-06-11. AIS provides equivalent FAA authority via a working API → use AIS.
- **Consumption model:** bundle full US dataset to `data/airports_faa.json` (built by `tools/build_faa_airports.py`, stdlib-only so it can also run as a refresh Lambda), ship in the Lambda zip; refresh monthly + redeploy. Both live-query and bundle are FAA-authoritative; bundle chosen for speed + resilience at preflight + matches FAA 28-day cadence. Live-query fallback = easy future add.

## 2026-05-30 — AWS deploy 403: RESOLVED ✅ (corrected root cause)

**CORRECTION (confirmed against the live account):** the root cause was NOT an org SCP. The org (o-zzs81hbacf) has ONLY the default `FullAWSAccess` SCP — zero deny policies, none on the account; <AWS_ACCOUNT_ID> IS the management account. The real cause: the Function URL's resource policy was **missing the `lambda:InvokeFunction` statement** that AWS has REQUIRED for public (NONE) URLs **since Oct 2025** (docs: "If a function's resource-based policy doesn't grant [both lambda:InvokeFunctionUrl and lambda:InvokeFunction]... users will get a 403 Forbidden... even if the function URL uses the NONE auth type"). `deploy.sh` used the pre-Oct-2025 single-permission pattern.

**Fix (applied + verified live):** `aws lambda add-permission --function-name n9082p-planner --action lambda:InvokeFunction --principal '*' --invoked-via-function-url`. Result: no-auth→401, auth→200, plan→A5. LIVE at https://nvnl7kstmkaw7f7iyvjxwayx440fakjq.lambda-url.us-west-2.on.aws/ . `deploy.sh` updated to add BOTH permissions idempotently. **API Gateway NOT needed.**

**Lesson:** I (and the research agents, which I primed with the "account is in an org" framing) over-fit to an org-guardrail explanation. A fresh personal org has no deny SCPs; should have checked the resource policy / recent AWS changes first. The SCP analysis below is retained but was a WRONG hypothesis.

### (original SCP hypothesis — DISPROVEN, kept for the record)

Symptom: public Lambda Function URL (AuthType NONE) → 403 AccessDeniedException for all requests; direct `aws lambda invoke` → 200; resource policy is the correct public-NONE policy; account in AWS Org o-zzs81hbacf. Still 403 hours after creation (NOT propagation).

ROOT CAUSE (3 research agents + AWS docs): an **SCP** denies the **`lambda:InvokeFunctionUrl`** action for public URLs (typically conditioned `lambda:FunctionUrlAuthType=NONE`, or inverse `StringNotEquals AWS_IAM`). Explicit SCP Deny overrides the resource-policy Allow → 403 before our code runs.
- SMOKING GUN = action asymmetry: direct invoke = `lambda:InvokeFunction` (200); URL path = `lambda:InvokeFunctionUrl` (denied).
- NOT an RCP — Lambda is not an RCP-supported service (S3/STS/KMS/SQS/Secrets Mgr/Cognito/DynamoDB/... only, as of 2026).
- NOT our config — create-function-url-config succeeded, so it's not the stock Control Tower CT.LAMBDA.PV.1 (which denies only Create/Update of NONE URLs). This is a custom/hardened SCP that also denies invoke.
- CONFIRM only from the Org MANAGEMENT account (SCPs unreadable from a member acct; describe-effective-policy excludes SCPs): `aws organizations list-policies-for-target --target-id <AWS_ACCOUNT_ID> --filter SERVICE_CONTROL_POLICY` + `describe-policy`; walk parent OUs; `controltower list-enabled-controls`.

FIX (validated) — **API Gateway HTTP API (apigatewayv2) + Lambda proxy (payload v2.0)**:
- Sidesteps the SCP: API GW invokes via `lambda:InvokeFunction` as service principal apigateway.amazonaws.com (no function URL; `lambda:FunctionUrlAuthType` never in context). Public ingress = execute-api, not a function URL.
- ~$0/mo (HTTP API ~$1/M req, no fixed fee, free tier 1M/mo). Basic Auth unchanged (Authorization header forwarded in v2.0 event). handler.lambda_handler already speaks v2.0 → NO code change.
- Alternatives: REST API (same mechanism, 3.5×/M); CloudFront+OAC with AuthType=AWS_IAM (more setup); ALB (~$16/mo fixed — avoid). If owner controls the management account, could instead exempt the SCP (ExemptedPrincipalArns / move account / narrow Deny) — but API GW is simpler and doesn't touch org security.
- TODO: update deploy.sh to provision API GW instead of (or alongside) the Function URL; delete the blocked Function URL.

Sources: docs.aws.amazon.com/lambda/latest/dg/urls-auth.html; .../controltower/.../ct-lambda-pv-1.html; .../organizations/.../orgs_manage_policies_rcps.html; .../lambda/.../services-apigateway.html; aws.amazon.com/api-gateway/pricing/.

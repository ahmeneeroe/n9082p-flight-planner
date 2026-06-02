# N9082P Flight Planning Tool

A mobile web app that generates a preflight **A5 safety sheet** for N9082P (1966 PA-24-260B
Comanche): per-runway takeoff/landing distances & margins, density altitude, wind components,
stall/approach speeds, and OK/CAU/WARN safety badges — from **live FAA airport data + NWS
weather + the POH performance calculator**. Supplements ForeFlight with the takeoff/landing/stall
data its basic performance profile doesn't provide.

## Live

**https://flight-planning.davidameneyro.com** — password-gated (enter the password once; a signed
cookie keeps you in for 30 days). On iPhone: open it → Share → **Add to Home Screen** for an app icon.

Raw origin (no custom domain, always works): `https://nvnl7kstmkaw7f7iyvjxwayx440fakjq.lambda-url.us-west-2.on.aws/`

## How to use

Open the URL → enter the password → fill **departure, destination, takeoff weight, fuel** → *Generate*.
Optional **Advanced**: cruise altitude, power %, RPM, mixture, landing-weight override. On the result,
*Print / Save PDF* gives the A5.

## Data sources (FAA-authoritative)

- **Airports / runways:** FAA AIS (Aeronautical Information Services), bundled to `data/airports_faa.json`
  (~12,846 US airports) by `tools/build_faa_airports.py`. **Refresh monthly** (FAA 28-day cycle): rerun the
  builder + redeploy.
- **Weather:** live METAR from aviationweather.gov (NOAA/NWS Aviation Weather Center); auto-nearest-station
  for fields without their own METAR (e.g. S95 → KALW).
- **Performance:** the digitized POH Section 5 calculator in `../Performance/`. **EXPERIMENTAL** — 5%
  conservative bias, not flight-validated; the sheet says so. Verify against the POH.

## Architecture

```
Browser → CloudFront (custom domain + HTTPS) → Lambda Function URL → app/handler.py (lambda_handler)
        → planner/  (data · weather · geo · safety · generate · render)  → A5 HTML
```
- Pure Python **standard library only** — no third-party deps; deploys as a plain zip.
- **Auth:** password → HMAC-signed cookie (`app/handler.py`). *Not* HTTP Basic Auth — Lambda Function URLs
  remap the `WWW-Authenticate` header, so the browser dialog never appears.

### AWS resources (account <AWS_ACCOUNT_ID>; us-west-2 unless noted)
| Resource | Value |
|---|---|
| Lambda | `n9082p-planner` (handler `handler.lambda_handler`, env `PLANNER_PASSWORD`) |
| IAM role | `n9082p-planner-role` |
| Function URL | AuthType NONE; resource policy grants **both** `lambda:InvokeFunctionUrl` + `lambda:InvokeFunction` |
| ACM cert | us-east-1 `e50c5b65-b203-48b5-8830-92a711b4a7ae` (flight-planning.davidameneyro.com) |
| CloudFront | `ESYJH857V9VMT` → `d1g4lk8265qufv.cloudfront.net` (CachingDisabled + AllViewerExceptHostHeader) |
| DNS | Namecheap BasicDNS: `flight-planning` CNAME → CloudFront (+ ACM validation CNAME) |

## Local development
```
python3 app/devserver.py        # http://localhost:8000/  (open, no password)
```
Pure stdlib; needs internet for live METAR.

## Redeploy (after code or data changes)
```
aws sso login                   # if the SSO token has expired (~4h)
bash deploy/deploy.sh           # build zip → create/update Lambda + Function URL + permissions
# code-only shortcut:
bash deploy/build.sh && aws lambda update-function-code \
  --function-name n9082p-planner --region us-west-2 --zip-file fileb://n9082p-planner.zip
```

## Monthly FAA data refresh (automated)

**Automated:** S3 bucket `n9082p-planner-data-<AWS_ACCOUNT_ID>` holds the live bundle; the
`n9082p-data-refresh` Lambda (EventBridge `rate(28 days)`, via `deploy/deploy_refresh.sh`)
rebuilds it from FAA AIS and uploads to S3, and the app reads it from S3 (`DATA_BUCKET` env)
with the bundled file as fallback. To refresh manually / rebuild the bundled baseline:
```
aws sso login
python3 tools/build_faa_airports.py   # rebuild data/airports_faa.json from FAA AIS
bash deploy/build.sh && aws lambda update-function-code \
  --function-name n9082p-planner --region us-west-2 --zip-file fileb://n9082p-planner.zip
```
The bundled `data/airports_faa.json` remains the fallback baseline; the manual steps above also refresh it for the next deploy.

## Two AWS gotchas (already solved, documented in research.md)
1. **403 on the public Function URL** was *not* an org policy — since **Oct 2025** a public (NONE) URL
   needs **both** `lambda:InvokeFunctionUrl` and `lambda:InvokeFunction` in its resource policy. `deploy.sh`
   now adds both.
2. **Basic Auth never prompted** — Function URLs remap `WWW-Authenticate` → `x-amzn-Remapped-*`. Switched to
   a signed-cookie login.

## Custom domain runbook (how it was set up)
1. ACM cert (us-east-1) for the subdomain, DNS-validated via a CNAME at Namecheap.
2. CloudFront distribution: Function URL as origin + the cert + alias `flight-planning.davidameneyro.com`.
3. Namecheap CNAME `flight-planning` → the CloudFront domain.

## Notes / follow-ups
- **Password** is set via the `PLANNER_PASSWORD` env var on the Lambda (never committed to this repo). Pick a strong value and set/rotate it with `deploy/deploy.sh`.
- Automate the monthly FAA data refresh.
- Layout: `planner/` (engine) · `app/` (handler + devserver) · `data/` (FAA bundle) · `tools/` (data builder)
  · `deploy/` (build + deploy) · `files/` (sample A5 + prototypes) · `design.md` · `todo.md` · `research.md`.

## Operations & handoff

> **For an exhaustive snapshot** — architecture, full AWS inventory, the card's layout/rendering, every
> performance & data finding, decisions, and gotchas — see **`HANDOFF.md`** (the single read-this-first doc).

**Working copy vs. published repo.** Develop and deploy from this working copy
(`~/Documents/Flying/N9082P/Flight-Planning-Tool`, with the sibling `../Performance`). The
public GitHub repo (`github.com/ahmeneeroe/n9082p-flight-planner`) is a *clean export* at
`~/Documents/Flying/n9082p-flight-planner` (account ID genericized; POH chart scans, PDFs,
and secrets excluded). Re-sync it after changes via the rsync → verify → commit → push flow.

**AWS inventory** (account `<AWS_ACCOUNT_ID>`, `us-west-2` unless noted):
- **App:** Lambda `n9082p-planner` (env `PLANNER_PASSWORD`, `DATA_BUCKET`, `DATA_KEY`) + role `n9082p-planner-role` + public Function URL.
- **Edge:** CloudFront `ESYJH857V9VMT` → `flight-planning.davidameneyro.com`; ACM cert `e50c5b65-…` (us-east-1).
- **Data:** S3 `n9082p-planner-data-<AWS_ACCOUNT_ID>` (private); refresher Lambda `n9082p-data-refresh` + role `n9082p-data-refresh-role`; EventBridge `n9082p-data-refresh-28d` (`rate(28 days)`).
- **Monitoring:** SNS `n9082p-alerts` (email confirmed) + CloudWatch alarm `n9082p-data-refresh-errors`.

**Common tasks** (run `aws sso login` first):
- Redeploy app: `PLANNER_PASSWORD=<pw> bash deploy/deploy.sh`
- Redeploy refresher / schedule: `bash deploy/deploy_refresh.sh`
- Force a data refresh now: `aws lambda invoke --function-name n9082p-data-refresh --region us-west-2 /tmp/r.json`
- (Re)configure alerts: `bash deploy/deploy_alerts.sh`
- App logs / data source: `aws logs tail /aws/lambda/n9082p-planner --since 1h --region us-west-2` (look for `[data] source=…`)

**Behavior on failure.** A failed monthly refresh emails you (CloudWatch → SNS). Staleness is
also visible as "Airport data: &lt;date&gt;" on every sheet. The app falls back to the bundled
`data/airports_faa.json` if S3 is unavailable, so it never hard-fails.

## Resume this work
```
cd /Users/papillonm5/Documents/Flying/N9082P/Flight-Planning-Tool && claude --resume N9082P-Perfomance-Online
```

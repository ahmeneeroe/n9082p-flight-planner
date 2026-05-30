# N9082P Flight Planner

Preflight **A5 safety sheet** generator for N9082P (1966 Piper PA-24-260B Comanche):
per-runway takeoff/landing margins, density altitude, wind components, stall/approach
speeds, and OK/CAU/WARN badges — from **FAA airport data + live NWS weather + a digitized
POH performance calculator**.

> **Experimental.** Performance figures are digitized approximations of the POH Section 5
> charts (with a conservative bias) and are **not** flight-validated. Always verify against
> the POH. Not affiliated with or endorsed by Piper.

## Layout
- **`Flight-Planning-Tool/`** — the web app (Python stdlib): form → A5 sheet, deployed on AWS Lambda behind CloudFront. See its `README.md`.
- **`Performance/`** — the POH-derived performance calculator (the engine). See its `README.md`.

The web app depends on the calculator (sibling directory). Start with `Flight-Planning-Tool/README.md`.

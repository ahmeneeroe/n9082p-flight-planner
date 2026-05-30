# Flight Planner Design -- N9082P

## Overview

A CLI flight planning tool that wraps the existing performance calculator (`src/calculator.py`) to produce complete preflight briefs. The pilot types a departure, destination, weight, and fuel load; the tool computes performance for each flight phase and runs safety checks.

**Example:**
```
python3 plan.py S95 KBOI --weight 2800 --fuel 86 --cruise-alt 9500 --power 65
python3 plan.py S95 KSFF --weight 2600 --fuel 56 --wx auto
```

## Design Principles

- CLI first. No web server, no mobile app. Can add TUI later.
- Pure Python, minimal dependencies. Only `requests` for weather (optional).
- The performance calculator is the engine; the planner is a thin layer on top.
- No W&B module -- pilot computes weight elsewhere and provides takeoff weight.
- Safety checks are automatic and always shown. Never silent.
- Standard technique (2x charted distance) is the default; short-field is opt-in.

## Build Order

### Phase 1: MVP
1. **Airport data** -- Small bundled JSON (~30 local airports: S95, KALW, KSFF, KGEG, KBOI, KRDM, KSEA, KPDX, KPSC, KLWS, S50, etc.). Each entry: identifier, name, lat, lon, elevation, runways (id, length, width, surface, heading).
2. **Route computation** -- Haversine great-circle distance, initial magnetic course, wind component decomposition (headwind/crosswind from runway heading + wind).
3. **Flight plan orchestrator** -- `FlightPlan` class that chains: takeoff → climb → cruise → descent → landing. Tracks fuel burn and weight through each phase. Computes pressure altitude from field elevation + altimeter setting.
4. **Safety checks** -- Runway length vs required distance (green/yellow/red thresholds), fuel reserves (VFR day 30 min / night 45 min), crosswind vs 17 kt demonstrated, density altitude warnings.
5. **CLI + text output** -- `argparse` entry point, formatted plain-text flight brief.

### Phase 2: Weather
6. **METAR fetch** -- aviationweather.gov API (free, no key). Map non-METAR airports to nearest station (S95 → KALW). Graceful fallback to manual entry.

### Phase 3: Full Airport DB
7. **OurAirports import** -- SQLite from OurAirports CSV data (~5 MB for all US). Replaces the hand-curated JSON.

### Phase 4: Polish
8. Saved defaults (`~/.n9082p.toml`: pilot weight, home airport, preferred power/RPM)
9. Multi-leg trip support
10. Optional TUI with `rich`/`textual`
11. Trip logging for post-flight comparison

## User Inputs

### Required
- Departure airport (identifier)
- Destination airport (identifier)
- Takeoff weight (lb) -- pilot computes W&B separately
- Fuel load (gallons, default 86)

### Optional (with defaults)
| Input | Default | Flag |
|-------|---------|------|
| Cruise altitude | Auto-suggest | `--cruise-alt 9500` |
| Cruise power | 65% | `--power 65` |
| RPM | 2400 | `--rpm 2400` |
| Mixture | best_economy | `--mixture best_power` |
| Weather | Manual entry | `--wx auto` or `--temp 85 --altimeter 29.85 --wind 270/12` |
| Technique | standard (2x) | `--short-field` |
| Landing weight | Auto (takeoff - fuel burn) | `--landing-weight 2600` |

## Safety Checks (Always Automatic)

| Check | Green | Yellow | Red |
|-------|-------|--------|-----|
| Runway vs over-50ft | ≥2.0x | 1.5-2.0x | <1.5x |
| Fuel reserve | >60 min | 30-60 min | <30 min |
| Crosswind | <12 kt | 12-17 kt | >17 kt (demonstrated) |
| Density altitude | <5000 ft | 5000-8000 ft | >8000 ft |
| Takeoff weight | <3100 lb | -- | >3100 lb |
| Landing weight | <2945 lb | -- | >2945 lb |

## What NOT to Build

- W&B calculator (pilot has this elsewhere)
- Moving map / in-flight tool
- NOTAMs, TFRs, airspace
- Terrain analysis
- Flight plan filing
- Regulatory database

## Architecture

```
Performance/
  planner/
    __init__.py
    cli.py              # argparse entry point
    flight_plan.py      # FlightPlan class -- orchestrates phases
    airport.py          # Airport lookup from bundled data
    route.py            # Haversine distance, course, wind components
    safety.py           # All safety checks
    output.py           # Formatted text output
    weather.py          # METAR fetch (Phase 2)
  data/
    airports.json       # Hand-curated local airports (Phase 1)
    airports.db         # Full OurAirports SQLite (Phase 3)
  plan.py               # Entry point: python3 plan.py S95 KBOI ...
```

## Key Technical Notes

- Pressure altitude from altimeter: `PA = field_elev + (29.92 - altimeter) * 1000`
- Magnetic variation for PNW: ~15-16°E (hardcode by region)
- Descent model: 500 fpm, ~40% power, ~8 GPH fuel flow (simple estimate)
- Standard technique: 2x charted short-field distance (per POH notes)
- The 5% conservative bias stays in the calculator; planner doesn't touch it
- Fuel flow during climb: `fuel_consumption.fuel_flow_climb()` = 21.5 GPH
- S95 does not have METAR; nearest is KALW (2 nm, same valley)

## Regulatory Basis

FAA AC 91-78A (2024) explicitly permits EFBs with algorithmic performance calculations under Part 91. No approval required. The calculator is legal for flight planning as long as the POH remains the authoritative source.

# N9082P Performance Calculator

**Aircraft:** 1966 Piper PA-24-260B Comanche (N9082P)
**Status:** ALL 14 POH Section 5 charts digitized via WebPlotDigitizer. All tests PASS.
**Last updated:** 2026-03-29

## IMPORTANT

This is an **experimental digitized approximation** of POH Section 5 charts. It supplements but does NOT replace the POH. Takeoff and landing distances include a 5% conservative bias. Not yet validated against real-world flight data.

## Quick Start

```python
from src.calculator import N9082P

perf = N9082P()

# Takeoff at Walla Walla (S95), summer day
perf.takeoff(pressure_alt_ft=1200, oat_f=90, weight_lb=2800, headwind_kt=5)

# Cruise at 7500 ft, 65% power, 2400 RPM
perf.cruise(pressure_alt_ft=7500, oat_f=30, percent_power=65, rpm=2400)

# Landing
perf.landing(pressure_alt_ft=1200, oat_f=90, weight_lb=2600, headwind_kt=8)

# Stall speeds, climb (weight-aware), power settings
perf.stall(weight_lb=2800)
perf.climb(pressure_alt_ft=1200, oat_f=90, target_alt_ft=7500, weight_lb=2800)
perf.power_setting(pressure_alt_ft=7000, rpm=2400, percent_power=65, oat_f=30)
```

Run validation: `python3 tests/test_validation.py`

## What's Digitized

All 14 performance charts from POH Section 5, using WebPlotDigitizer on 300 DPI exports from `Manuals/N9082P-Performance.pdf`.

| Figure | Chart | Points | Notes |
|--------|-------|--------|-------|
| 5-02 | Airspeed Calibration | 45 | IAS→CAS, 2 configs |
| 5-03 | Fuel Consumption | 20 lines | RPM-aware (1800-2700) |
| 5-04 | Altitude Performance | 3 panels | MAP→BHP, full-throttle, temp correction |
| 5-05 | Stall Speed | 14 | 2 curves, within 0.1 kt |
| 5-06 | Takeoff Ground Run | ~170 | 3-panel nomogram, 5% bias |
| 5-07 | Takeoff Over 50 ft | ~100 | 3-panel nomogram, 5% bias |
| 5-08 | Rate of Climb | 10 | Weight-aware (2100-3100 lb) |
| 5-09 | VX / VY | 8 | MPH scale, 2 configs |
| 5-10 | True Airspeed | 70+ | 4 power lines + 2 full-throttle |
| 5-11 | Range Profile | 12 | 3 power × 2 fuel loads, NM |
| 5-12 | Endurance Profile | 8 | 4 power settings |
| 5-13 | Landing Ground Roll | ~50 | 3-panel nomogram, 5% bias |
| 5-14 | Landing Over 50 ft | ~60 | 3-panel nomogram, 5% bias |
| 5-15 | Power Setting Table | exact | Direct PDF transcription |

## Next: Flight Planner

See `flight-planner-design.md`. CLI tool that wraps the calculator for complete preflight briefs: `python3 plan.py S95 KBOI --weight 2800 --fuel 86`. Auto runway checks, fuel reserves, DA warnings.

## Project Files

- `research.md` -- Exhaustive technical log, all decisions, validation results, lessons learned
- `research-digitization-landscape.md` -- Survey of existing POH digitization tools and approaches
- `flight-planner-design.md` -- Design proposal for the flight planning CLI
- `howto.md` -- Digitization workflow for future refinement
- `todo.md` -- Task list
- `charts/` -- 300 DPI PNGs, `charts/data/` -- WPD JSON exports

## Resume This Project

```
cd ~/Documents/Flying/N9082P && claude --resume performance-digitization
```

# Performance Digitization TODO

## ALL 14 CHARTS DIGITIZED -- Completed 2026-03-29

### Digitized via WebPlotDigitizer
- [x] Fig 5-02: Airspeed Calibration (45 pts, 2 curves)
- [x] Fig 5-03: Fuel Consumption (10 lines + power ticks, includes RPM)
- [x] Fig 5-04: Altitude Performance (3 panels, 30+ lines)
- [x] Fig 5-05: Stall Speed (14 pts, 2 curves)
- [x] Fig 5-06: Takeoff Ground Run (3-panel nomogram, ~170 pts, 5% conservative bias)
- [x] Fig 5-07: Takeoff Over 50 ft (3-panel nomogram, 9 alt curves + 12 wt + 12 hw guidelines)
- [x] Fig 5-08: Rate of Climb (5 lines, 4 weight curves + gear-down)
- [x] Fig 5-09: VX and VY (4 lines, MPH scale)
- [x] Fig 5-10: True Airspeed (4 power lines + 2 full-throttle curves)
- [x] Fig 5-11: Range Profile (6 lines: 3 power × 2 fuel loads)
- [x] Fig 5-12: Endurance Profile (4 power lines)
- [x] Fig 5-13: Landing Ground Roll (3-panel nomogram, 5% conservative bias)
- [x] Fig 5-14: Landing Over 50 ft (3-panel nomogram)
- [x] Fig 5-15: Power Setting Table (direct transcription, exact)

### Not Needed (computed from standard formulas)
- [x] Fig 5-01: Altitude Conversion -- NWS density altitude formula
- [x] Fig 5-1A: Temperature Conversion -- trivial
- [x] Fig 5-1B: Crosswind Component -- basic trig

## Flight Planner (Next Project)
See `flight-planner-design.md` for full design.

### Phase 1: MVP
- [ ] Airport data -- hand-curated JSON (~30 local airports)
- [ ] Route computation -- Haversine distance, course, wind components
- [ ] Flight plan orchestrator -- chain takeoff→climb→cruise→descent→landing, fuel tracking
- [ ] Safety checks -- runway length, fuel reserves, crosswind, DA warnings
- [ ] CLI + text output

### Phase 2: Weather
- [ ] METAR fetch from aviationweather.gov (S95 → KALW)

### Phase 3+
- [ ] Full airport DB (OurAirports → SQLite)
- [ ] Saved defaults, TUI, trip logging

## Other Future Work
- [ ] Validate performance calculator against real-world flight data
- [ ] Remove conservative bias once validated

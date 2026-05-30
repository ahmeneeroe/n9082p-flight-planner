# Research: POH Digitization Landscape

## Date: 2026-03-29

Summary of existing efforts to digitize legacy GA performance charts into digital tools.

---

## Open Source Projects

**POH Performance (pohperformance.com)** -- The closest analog to our project. JavaScript/HTML/CSS SPA, iOS/Android via Cordova. Covers C172, C182, Bonanza, Baron, TBM (~5 aircraft). Same approach: WebPlotDigitizer → piecewise-linear lookup tables. Free, on SourceForge. Their developer docs describe the workflow: image chart, trace axes, trace curves, store as point series with more points in curved regions.

**Others:** OpenAP (TU Delft, transport-category focus), Robert Wilkos Aviation Calculator (web-based, 110+ aircraft but limited), AeroVia Tools (general aero engineering). No other significant open-source projects specifically digitize GA POH charts.

---

## Commercial Products

**ForeFlight Performance Plus** -- Market leader. Hand-built models for hundreds of GA aircraft. Won't extrapolate beyond POH ranges. Users can bias-adjust for their specific airframe. All assumptions modeled "exactly as they exist in your POH."

**Gyronimo Flight Pad** -- ~$15/aircraft iPad apps (C152, C172, Archer, Arrow, DA40). Slider UI. Explicitly disclaims: "pilot assistance tool for plausibility checks."

**Garmin** -- Limited performance features, mostly airframe-specific to factory avionics packages.

**Jeppesen SCAP** -- Airline gold standard (FORTRAN, IATA standard since 1985). Rigorous: difference between line data and computed output must be conservative and minimal. Evolving toward PIXM (XML/JSON). Far beyond GA needs but defines what "properly digitized" looks like.

---

## Academic Work

**Mirosavljevic et al. (2018)** -- Only peer-reviewed paper on the topic: "Digitalization of Aircraft Performance Nomograms" in Aircraft Engineering and Aerospace Technology. Authors note this "has never been analyzed before" in formal literature.

**NACA TR-408 (Oswald, 1932)** -- Foundational work: general formulas for airplane performance calculation. The theoretical basis underlying all POH charts.

**PyNomo** -- Python nomogram library. Demonstrates that nomograms encode specific functional forms (products, sums, power laws) that can be reverse-engineered.

---

## FAA Guidance

**AC 91-78A (2024)** -- Key document for Part 91. Explicitly allows EFBs to replace paper materials and to "complete algorithmic functions (e.g., Weight and Balance, performance, and fuel calculations)." NO FAA approval required for Part 91 operators.

**AC 120-76E** -- For Part 121/135 (air carriers), performance calculation is "Type B" EFB requiring operator approval. Does NOT apply to Part 91.

**14 CFR 91.103** -- Requires PIC to become familiar with "all available information" including takeoff/landing distances. A digitized calculator satisfying this requirement is legal. The POH remains the legally approved source if there's a disagreement.

---

## Community Findings

**The "1.5x problem"** -- Dominant theme across AOPA, Pilots of America, PPRuNe: POH numbers are from professional test pilots in factory-new airplanes. Real-world performance is consistently worse. AOPA Air Safety Institute recommends 1.5x multiplier. Their flight testing found a C182 exceeded POH distances by ~30%.

**Our 5% conservative bias covers digitization error only -- NOT real-world degradation.** The pilot should apply additional operational margins.

**PPRuNe consensus on digitization:** Use WebPlotDigitizer or Engauge Digitizer. Keep polynomial order to cubic or below. Scanned documents have distortion. Split-axis charts need separate calibrations per panel. Any error should be conservative.

---

## Flight Simulator Approaches

**A2A Simulations** -- Owns a real PA-24-250 Comanche (N6229P), tuned flight model against real-world data. Physics-first approach validated against POH. Highest-fidelity GA piston sim.

**Black Square** -- Targets "within 2% of POH values." Physics-based engine simulation.

**MSFS 2024** -- Uses `flight_performance.cfg` with POH-derived targets. Physics model auto-tuned to match targets through 100 iterations.

---

## Assessment

**Our project is among the most thorough efforts found.** 14 charts with cross-validation, documented compound error analysis, conservative bias, and detailed lessons learned. Most community efforts stop at 1-2 charts.

**What works:** Piecewise-linear lookup tables, WebPlotDigitizer, physics-informed interpolation (W^n), conservative bias, cross-validation against POH examples.

**What doesn't:** High-order polynomials, blind curve fitting, trusting secondary scales on old charts, assuming one calibration works across multi-panel charts.

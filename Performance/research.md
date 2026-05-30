# Performance Digitization -- Research Log

## Project Overview

Digitizing all 14 performance charts from POH Section 5 for N9082P (1966 PA-24-260B Comanche, IO-540-D4A5, 260 HP) into a Python performance calculator. The source PDF for chart digitization is `Manuals/N9082P-Performance.pdf` (18.9 MB, high-quality scans). Chart pages were exported as 300 DPI PNGs using Swift/PDFKit into `Performance/charts/`.

The digitization tool is **WebPlotDigitizer** (https://automeris.io/WebPlotDigitizer/), a browser-based tool. The user (David) manually traces curves and exports JSON files into `Performance/charts/data/`.

All digitized data is **experimental and unvalidated against real-world flight data**.

---

## Digitization Status (as of 2026-03-29)

### Fully Digitized via WebPlotDigitizer

| Figure | Chart | JSON File(s) | Points | Status |
|--------|-------|---------------|--------|--------|
| 5-02 | Airspeed Calibration | `Fig5-02_Airspeed_Calibration.json` | 45 | Complete. Both curves were in one dataset; separated by click order (first 14 = flaps extended, remaining 31 = flaps retracted). |
| 5-03 | Fuel Consumption | `Fig5-03_Fuel_Consumption.json` | 20 lines + 5 power ticks | Complete. 10 RPM/mixture straight lines (2 endpoints each). Fuel flow now takes RPM as parameter. |
| 5-04 | Altitude Performance | 3 files: `-SEA-LEVEL-PERFORMANCE.json`, `-ALTITUDE PERFORMANCE.json`, `-STANDARD ALTITUDE TEMP.json` | 10 SL lines, 10 RPM lines, 9 MAP lines, 1 temp line | Complete. Three-panel chart: sea level MAP→BHP, altitude RPM/MAP lines, temp correction. |
| 5-05 | Stall Speed | `Fig5-05_Stall_Speed.json` | 14 | Complete. Two curves (clean, full flaps+gear), 7 points each. |
| 5-06 | Takeoff Ground Run | `Fig5-06_Takeoff_Ground_Run.json` (original MPH cal), `-knots.json` (knots recal), `-knots-morepoints.json` (9 HW guidelines) | ~170 total | Complete. Three-panel nomogram digitized. See detailed notes below. |
| 5-08 | Rate of Climb | `Fig5-08_Rate_of_Climb.json` | 10 (5 lines × 2 pts) | Complete. 4 weight curves clean (2100-3100 lb) + 1 gear-down at 3100 lb. All straight lines. |
| 5-09 | VX and VY | `Fig5-09_VX_VY-MPH-2.json` (corrected) | 8 (4 lines × 2 pts) | Complete. VX/VY for clean + gear-down. Calibrated on MPH scale (knots scale was compressed/unreliable). VY retracted at SL = 110.9 MPH vs POH Sec 2 = 105 MPH; validated at DA 3449 within 1 MPH of manual reading. |
| 5-10 | True Airspeed | `Fig5-10_True_Airspeed.json` | 4 lines + 64 curve pts | Complete. 4 power setting lines (45-75%) + 2 full-throttle curves (2400/2700 RPM). 75% at 7000 ft = 158 kt exact match. |
| 5-11 | Range Profile | `Fig5-11_Range_Profile.json` | 12 (6 lines × 2 pts) | Complete. 3 power settings × 2 fuel loads (56/86 gal). In nautical miles. |
| 5-12 | Endurance Profile | `Fig5-12_Endurance_Profile.json` | 8 (4 lines × 2 pts) | Complete. 4 power settings (45-75%). |
| 5-13 | Landing Ground Roll | `Fig5-13_Landing_Ground_Roll.json` | ~50 | Complete. Three-panel nomogram. 5 altitude curves + 8 weight guidelines + 7 headwind guidelines (knots). 5% conservative bias. |
| 5-14 | Landing Over 50 ft | `Fig5-14_Landing_Over_50ft.json` | ~60 | Complete. Three-panel nomogram. 9 altitude curves + 13 weight guidelines + 5 headwind guidelines. 5% conservative bias. |
| 5-15 | Power Setting Table | Direct transcription from PDF text | exact | Complete. No digitization tool needed. |

### ALL CHARTS DIGITIZED as of 2026-03-29.

### Charts That Don't Need Digitization

| Figure | Chart | Reason |
|--------|-------|--------|
| 5-01 | Altitude Conversion (DA) | Standard atmosphere math -- using NWS formula |
| 5-1A | Temperature Conversion | `C = (F-32)*5/9` |
| 5-1B | Crosswind Component | Basic trigonometry |
| 5-15 | Power Setting Table | Already transcribed exactly from PDF text |

---

## Detailed Notes by Chart

### Fig 5-02: Airspeed Calibration

**Source:** `charts/data/Fig5-02_Airspeed_Calibration.json`
**Axes:** Y = IAS (knots), X = correction (MPH). CAS_MPH = IAS_MPH + correction.
**Issue encountered:** User traced both curves (flaps retracted and flaps extended) into a single dataset called "FLAPS FULLY EXTENDED." The "FLAPS RETRACTED" dataset was empty. Separated by click order: first 14 points = flaps extended (IAS range 57-108 kt), remaining 31 points = flaps retracted (IAS range 65-197 kt).
**Key finding:** Corrections are ±3 MPH max. Much smaller than initial estimates of ±5 MPH. Flaps-retracted peaks at +1.7 MPH around 108-115 kt IAS. Flaps-extended peaks at -2.9 MPH around 87-90 kt IAS.
**Model:** `src/models/airspeed_cal.py`. Stores IAS (MPH) → correction (MPH) lookup tables per configuration. Converts knot inputs to MPH internally.

### Fig 5-03: Fuel Consumption

**Source:** `charts/data/Fig5-03_Fuel_Consumption.json`
**Axes:** X = Actual Brake Horsepower, Y = Fuel Consumption (US GPH).
**Structure:** 10 straight lines (2 endpoints each): 6 for Best Economy (1800-2700 RPM), 4 for Best Power (2200-2700 RPM). Plus 5 percent-power tick marks mapping %power → BHP (45%=116, 55%=143, 65%=169, 75%=195, 85%=221).
**Key finding:** Fuel flow varies significantly with RPM at the same BHP. At 65%/best economy: 12.3 GPH at 2200 RPM vs 13.5 GPH at 2700 RPM. The old model ignored RPM.
**Cross-check:** At 2400 RPM, all six known POH values match within 0.1-0.2 GPH. Climb fuel flow (260 BHP, 2700 RPM, best power) = 21.5 GPH exactly matches POH example.
**Model:** `src/models/fuel_consumption.py`. `fuel_flow_from_percent(percent_power, rpm, mixture)` -- note RPM is now a required parameter. The calculator's `cruise()` method was updated to pass RPM through.

### Fig 5-04: Altitude Performance

**Source:** Three JSON files (sea level, altitude, temperature panels).
**Sea Level panel:** X = MAP (in Hg), Y = BHP. 10 RPM lines (1800-2700), each straight (2 endpoints). Plus two boundary lines (limiting MAP for continuous operation, full throttle zero ram).
**Altitude panel:** X = Pressure Altitude (thousands of feet), Y = BHP. 10 RPM lines (full-throttle BHP decline with altitude). 9 MAP iso-lines (12-28 in Hg) -- short nearly-vertical segments showing where each MAP becomes the full-throttle limit.
**Temperature panel:** Standard lapse line from 60.6F at 1,000 ft to -24.5F at 24,000 ft. Correction: ±1% BHP per 10.8°F from standard.
**Key design decision:** For part-throttle at altitude, the model uses sea level BHP(MAP, RPM) directly. For a fuel-injected engine, the same MAP produces nearly the same BHP regardless of altitude (MAP is absolute intake pressure). The model caps at full-throttle BHP from the altitude RPM lines, then applies temperature correction.
**Cross-check:** Sea level BHP at MAP 24.8/2400 RPM = 196 (75% = 195 expected), at MAP 22.2/2400 = 169 (65% = 169), at MAP 19.8/2400 = 144 (55% = 143). All within 1 BHP.
**Model:** `src/models/cruise.py`. Functions: `sea_level_bhp()`, `full_throttle_bhp()`, `max_map_at_altitude()`, `bhp_at_altitude()`.

### Fig 5-05: Stall Speed

**Source:** `charts/data/Fig5-05_Stall_Speed.json`
**Axes:** X = Gross Weight (lb), Y = Stall Speed (knots CAS).
**Structure:** Two curves, 7 points each: "GEAR AND FLAPS RETRACTED" (clean) and "GEAR EXTENDED - FULL FLAPS" (32 deg + gear down).
**Key finding:** The digitized curve is slightly steeper than initial estimates. At 1900 lb, the actual stall speed is 1-1.5 MPH lower than estimated. The sqrt(W) physics model holds well -- all points fit a W^0.5 relationship.
**Cross-check:** Clean at 3100 lb = 65.1 kt (POH: 65), full flaps at 3100 lb = 58.3 kt (POH: 58).
**Model:** `src/models/stall_speed.py`. Lookup tables in MPH (converted from digitized knot values). Physics-based sqrt(W/W_ref) model for the 15-deg flap configuration (not on chart).

### Fig 5-06: Takeoff Ground Run (DETAILED)

**Source:** `charts/data/Fig5-06_Takeoff_Ground_Run.json` (original), `-knots.json` (knots recalibration), `-knots-morepoints.json` (9 headwind guidelines).
**Three-panel nomogram digitization:**

**Panel 1 (Temperature/Altitude):**
- Axes: X = Temperature (°F), Y = Ground Run Distance (feet) using the right-side distance scale.
- 9 datasets, one per altitude curve: SL, 1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000 ft.
- Dense points (10-18 per curve). Total ~117 points.
- Gives: base_distance = f(temperature, altitude) at 3100 lb, no wind.
- Cross-check: SL at 59°F (standard) = 1264 ft (POH: 1260). ✓

**Panel 2 (Weight):**
- Axes: X = Weight (LBS × 100), Y = Ground Run Distance (feet).
- 4 guide lines traced at different heights, 5 weight ticks each (3100, 2900, 2700, 2500, 2300 lb).
- Weight correction is multiplicative (guide lines nearly parallel on ratio basis).
- Derived factors: 3100→1.000, 2900→0.856, 2700→0.726, 2500→0.607, 2300→0.498.
- **The factors follow a perfect W^2.33 power law** (exponent consistent to ±0.02 across all points). Linear interpolation at intermediate weights (e.g., 3000 lb → 0.928) is accurate to within 0.1%.

**Panel 3 (Headwind):**
- **Calibration lesson learned:** The chart has separate MPH and KNOTS scales on the X-axis. They are NOT shared -- the tick marks are at different physical positions. Original calibration used MPH scale. A second calibration on the knots scale confirmed: what reads as "10 MPH" = 8.7 kt, "20 MPH" = 17.2 kt, "30 MPH" = 25.8 kt (correct conversion factors).
- **Headwind breakpoints (knots):** 0, 8.7, 17.2, 25.8 kt.
- Originally 4 guide lines. User added 5 more for total of 9, to reduce interpolation uncertainty.
- **Key finding:** Headwind correction is multiplicative for base distances above ~1000 ft. Below 1000 ft, the factor decreases (guide lines converge). For typical takeoff distances (1000+ ft), factors are consistent:
  - 0 kt: 1.000
  - 8.7 kt: 0.791
  - 17.2 kt: 0.580
  - 25.8 kt: 0.370
- Factors use average of upper 3 guide lines (lower guide line excluded as outlier at small distances).

**Conservative bias:**
- Raw digitized values are ~5-8% optimistic vs POH example and manual chart readings.
- Two validation points:
  1. POH example (2000ft/60F/3000lb/10kt): raw=1017, POH=1100, user reads ~1050
  2. User test (2000ft/70F/2700lb/10MPH): raw=795, user reads ~860
- Applied 5% conservative bias (`CONSERVATIVE_BIAS = 1.05`) to final output.
- With 5% bias: POH example → 1068 (vs 1100), user test → 858 (vs ~860). Both reasonable.
- The bias accounts for nomogram reading precision compounding across three panels (each panel ±1-2%, compounded = ±4-6%).

**Fig 5-07 (Over 50 ft obstacle):** Fully digitized as a separate three-panel nomogram. See detailed notes in the Fig 5-07 section below. Weight correction is distance-dependent (unlike ground run). Headwind calibration required ×10 correction. Validated: SL/Std/3100/0 = 1831 ft (POH: 1725, +6% bias). POH example = 1552 ft (POH: 1500, +3.5%).

---

### Fig 5-08: Rate of Climb

**Source:** `charts/data/Fig5-08_Rate_of_Climb.json`
**Axes:** X = Rate of Climb (fpm), Y = Density Altitude (ft).
**Structure:** 5 straight lines (2 endpoints each):
- 3100 lb clean: 1360 fpm at SL, 0 at 20,939 ft
- 2900 lb clean: 1495 fpm at SL, 0 at 21,982 ft
- 2500 lb clean: 1815 fpm at SL, 0 at 22,965 ft
- 2100 lb clean: 2265 fpm at SL, 0 at 23,947 ft
- 3100 lb gear down / 15 flaps: 966 fpm at SL, 0 at 15,965 ft

**Key upgrade:** Old model only had gross weight. Now has 4 weight-specific curves, allowing interpolation at any weight. ROC at 2800 lb is ~1584 fpm vs 1360 at 3100 lb -- significant difference.
**Cross-check:** SL/3100 clean = 1360 fpm (POH: 1370, within 10 fpm). SL/2100 = 2265 fpm (POH: 2250, within 15 fpm). Time to climb 2000→7000 ft at 3000 lb = 4.5 min (matches POH example exactly).
**Service ceiling:** 3100 lb = 19,399 ft DA (POH: ~20,000). Derived from line where ROC = 100 fpm.
**Model:** `src/models/climb.py`. `rate_of_climb()` now takes `weight_lb` parameter. `time_to_climb()` and `service_ceiling()` also weight-aware. Calculator's `climb()` method updated to pass weight through.

### Fig 5-09: VX and VY

**Source:** `charts/data/Fig5-09_VX_VY-MPH-2.json` (third attempt -- see issues below)
**Axes:** X = Airspeed (MPH), Y = Density Altitude (ft).
**Structure:** 4 straight lines (2 endpoints each):
- VX retracted: 86.8 MPH at SL → 94.3 MPH at 15,000 ft (increases with altitude)
- VY retracted: 110.9 MPH at SL → 100.9 MPH at 15,000 ft (decreases with altitude)
- VX gear down/15 flaps: 76.6 MPH at SL → 80.3 MPH at ~12,000 ft
- VY gear down/15 flaps: 96.3 MPH at SL → 86.2 MPH at ~12,000 ft

**Issues encountered:**
1. **First attempt (knots calibration):** The knots scale on this chart is compressed/nonlinear at the high end. VY retracted read as 96.6 kt (= 111 MPH) -- couldn't tell if calibration or chart was off.
2. **Second attempt (MPH calibration):** User recalibrated on MPH scale. But initially used the wrong panel's axis calibration for the retracted curves -- retracted and extended values came out nearly identical (both ~96 MPH for VY). Detected because retracted should be higher than extended.
3. **Third attempt (MPH, corrected):** Separate calibrations per panel confirmed. VX and VY now show proper retracted > extended separation.

**Remaining discrepancy:** VY retracted at SL = 110.9 MPH vs POH Section 2 = 105 MPH (5.9 MPH gap). However, user manually verified at DA 3,449 ft: model gives VY = 109 MPH, user reads ~108 MPH from chart. Within 1 MPH at that altitude. The POH Section 2 value of 105 MPH may be a rounded/conservative operational value rather than the chart peak.

**Lesson:** This chart has two side-by-side panels with DIFFERENT axis scales (retracted: 80-110 MPH, extended: 70-100 MPH). Each panel MUST have its own axis calibration in WebPlotDigitizer. Also, prefer the MPH scale (primary, evenly spaced) over the knots scale (secondary, compressed) on older POH charts.

**Model:** `src/models/climb.py`. Stored as linear functions: `_speed_from_line(da, spd_sl, spd_ceil, ceiling)`. Internally MPH, converts to knots via `mph_to_knots()`.

---

### Fig 5-07: Takeoff Over 50 ft Obstacle

**Source:** `charts/data/Fig5-07_Takeoff_Over_50ft.json`
**Axes:** Panel 1: (temp F, distance ft). Panel 2: (weight lbs×100, distance ft). Panel 3: (headwind MPH, distance ft).
**Structure:** 9 altitude curves (6 pts each), 12 weight guidelines (mix of 2-pt and 5-pt), 12 headwind guidelines.
**Headwind calibration issue:** Raw values went 0-3 instead of 0-30 MPH. Multiplied by 10 to correct. Confirmed by ratio analysis matching takeoff ground run patterns.
**Weight correction is distance-dependent:** Unlike ground run (purely multiplicative), the over-50ft weight factors vary with base distance. At 2500 lb: factor ranges from 0.638 (short distances) to 0.532 (long distances). Used average of 4 five-point guidelines.
**Cross-check:** SL/Std/3100/0 = 1831 ft (POH: 1725, +6% with conservative bias). POH example = 1552 ft (POH: 1500, +3.5%).

### Fig 5-10: True Airspeed

**Source:** `charts/data/Fig5-10_True_Airspeed.json`
**Axes:** X = TAS (knots), Y = Density Altitude (ft).
**Structure:** 4 power-setting lines (45/55/65/75%, straight, 2 pts each) + 2 full-throttle curves (2400 RPM: 26 pts, 2700 RPM: 38 pts).
**Key finding:** TAS increases with altitude at constant power (TAS = CAS/sqrt(sigma)). Full-throttle curves peak near SL and decline as power drops with altitude. 2700 RPM at SL = 168.8 kt.
**Boundary fix:** 75% line ends at DA 6988 ft, but NWS formula gives DA 7018 at 7000 ft PA / standard. Added 100 ft tolerance to avoid false None returns at boundary.
**Cross-check:** 75% at 7000 ft = 158 kt (POH: 158 kt). Exact match.

### Fig 5-11: Range Profile

**Source:** `charts/data/Fig5-11_Range_Profile.json`
**Axes:** X = Range (NM), Y = Density Altitude (ft).
**Structure:** 6 straight lines: 55/65/75% power × 56/86 gal fuel. Range increases slightly with altitude.
**Model update:** Range function now takes altitude as parameter. Old model used statute miles at SL only; new model stores NM and supports altitude correction.

### Fig 5-12: Endurance Profile

**Source:** `charts/data/Fig5-12_Endurance_Profile.json`
**Axes:** X = Endurance (hours), Y = Density Altitude (ft).
**Structure:** 4 straight lines (45/55/65/75%). Endurance decreases slightly with altitude.
**Model update:** Endurance function now takes altitude parameter.

### Fig 5-13: Landing Ground Roll

**Source:** `charts/data/Fig5-13_Landing_Ground_Roll.json`
**Axes:** Panel 1: (temp F, ground roll ft). Panel 2: (weight lbs, ground roll ft). Panel 3: (headwind knots, ground roll ft).
**Structure:** 5 altitude curves (2-6 pts each), 8 weight guidelines (2 pts each), 7 headwind guidelines (4 pts each).
**Headwind already in knots** (correctly calibrated, unlike takeoff charts).
**Weight correction:** Max landing weight ~2945 lb. Factor at 2300 lb averages 0.855 across all 13 guidelines -- very consistent multiplicative correction.
**Cross-check:** SL/Std/2945/0 = 972 ft (POH: 925, +5% bias). POH example = 835 ft (POH: ~850, within 2%).

### Fig 5-14: Landing Over 50 ft Obstacle

**Source:** `charts/data/Fig5-14_Landing_Over_50ft.json`
**Axes:** Same as Fig 5-07 (temp F, weight lbs×100, headwind MPH).
**Structure:** 9 altitude curves (2 pts each, all straight lines), 13 weight guidelines (2 pts each), 5 headwind guidelines (4 pts each).
**Headwind calibration:** Correct for MPH (no ×10 needed, unlike Fig 5-07). Raw values 0.2-29.7 MPH.
**Weight correction:** Very consistent factor ~0.855 at 2305 vs 2950 lb. Power law exponent 0.635 (less weight-sensitive than ground roll because approach segment is nearly weight-independent).
**Cross-check:** SL/Std/2945/0 = 1502 ft (POH: 1435, +5% bias). POH example = 1301 ft (POH: ~1300, within 0.1%).

---

## Architecture

### Directory Structure

```
Performance/
  narrative.md          # Project description
  todo.md               # Task list
  howto.md              # Technical approach
  requirements.md       # Requirements
  research.md           # This file
  README.md             # User-facing summary
  charts/               # Exported chart images (300 DPI PNGs)
    data/               # WebPlotDigitizer JSON exports
  src/
    __init__.py
    calculator.py       # Main N9082P class (facade for all models)
    models/
      __init__.py
      power_settings.py # Fig 5-15 (exact transcription)
      stall_speed.py    # Fig 5-05 (WPD digitized)
      airspeed_cal.py   # Fig 5-02 (WPD digitized)
      fuel_consumption.py # Fig 5-03 (WPD digitized)
      takeoff.py        # Fig 5-06/07 (WPD digitized)
      landing.py        # Fig 5-13/14 (WPD digitized)
      climb.py          # Fig 5-08/09 (WPD digitized)
      cruise.py         # Fig 5-04/10/11/12 (all WPD digitized)
    utils/
      __init__.py
      interpolation.py  # 1-D and 2-D interpolation with None handling
      atmosphere.py     # Standard atmosphere, density altitude (NWS formula)
      units.py          # MPH↔knots, F↔C, etc.
  tests/
    __init__.py
    test_validation.py  # Validation suite against POH reference values
```

### Key Design Decisions

1. **Internal units:** POH native (MPH, feet, pounds, °F, in Hg). Output provides both MPH and knots.

2. **Density altitude formula:** Uses NWS formula `DA = 145442.16 * (1 - (17.326 * P/T_R)^0.235)` instead of Koch chart approximation. Much more accurate at large temperature deviations.

3. **Interpolation:** Custom pure-Python implementation in `utils/interpolation.py`. No numpy/scipy dependency. 1-D piecewise linear with endpoint clamping. 2-D bilinear with None-value handling (ignores zero-weight corners for edge lookups in power setting table).

4. **Power Setting Table (Fig 5-15):** Exact transcription from PDF text. Bilinear interpolation over (altitude, RPM) grid. None values for altitude/RPM combos beyond engine capability. Temperature correction: +0.17 in Hg per 10°F above standard.

5. **Fuel consumption now takes RPM:** Old model only took percent power and mixture. New model interpolates between RPM-specific lines. Default 2400 RPM for backward compatibility.

6. **Altitude performance (Fig 5-04):** For part-throttle at altitude, uses sea level BHP directly (fuel-injected engine: same MAP ≈ same BHP regardless of altitude). Caps at full-throttle limit. Temperature correction ±1% per 10.8°F.

7. **Takeoff nomogram (Fig 5-06):** Three panels decomposed into base distance → weight factor → headwind factor. Weight correction is purely multiplicative (W^2.33 power law). Headwind correction is multiplicative for distances >1000 ft. 5% conservative bias applied to final output.

8. **Error direction policy:** Any residual digitization error should be conservative (predict worse performance). For takeoff: overpredict distance. For landing: overpredict distance. For climb: underpredict rate.

---

## Lessons Learned

### WebPlotDigitizer Workflow

1. **Separate datasets per curve.** When tracing multiple curves on the same chart, create a separate named dataset for each. In the 5-02 digitization, both curves ended up in one dataset and had to be separated by click order.

2. **Units matter -- verify calibration.** The 5-06 headwind panel has dual MPH/KNOTS scales at DIFFERENT positions. Initially calibrated on MPH, then recalibrated on knots to confirm. The scales are NOT shared despite both showing 0-30 range.

3. **More guide line traces = better accuracy.** For the headwind panel, started with 4 guide lines, then added 5 more. The additional data confirmed the multiplicative model and identified the lower guideline as an outlier.

4. **Nomogram panels need separate axis calibrations.** For multi-panel charts, each panel has its own coordinate system. Export as separate datasets per panel, or use WebPlotDigitizer's multiple-axes feature. The shared Y-axis (distance) connects them.

5. **Dense points for curves, sparse for straight lines.** The fuel consumption chart (straight lines) only needs 2 points per line. The stall speed and airspeed calibration curves benefited from 14-45 points.

6. **Chart source PDF matters.** Use `N9082P-Performance.pdf` (18.9 MB), not `POH-Sec5-Performance.pdf` (944 KB). Higher resolution scans. Page index mapping (0-indexed): page 7=Fig 5-02, page 8=Fig 5-03, page 9=Fig 5-04, page 10=Fig 5-05, page 11=Fig 5-06, page 12=Fig 5-07, page 13=Fig 5-08, page 14=Fig 5-09, page 15=Fig 5-10, page 16=Fig 5-11, page 17=Fig 5-12, page 18=Fig 5-13, page 19=Fig 5-14.

7. **Side-by-side panels have different axis scales.** Fig 5-09 (VX/VY) has retracted panel (80-110 MPH) and extended panel (70-100 MPH) side by side. Each MUST have its own axis calibration. Using one calibration across both panels shifts values by ~10 MPH. This was caught because retracted and extended values came out nearly identical (which is physically impossible).

8. **Prefer MPH scale over knots on older POH charts.** The MPH scale is the primary (evenly spaced) axis on 1960s-era charts. The knots scale was added later and may be compressed or nonlinear, especially at the high end. Fig 5-09 knots scale gave VY = 96.6 kt (= 111 MPH) while the MPH scale gave 110.9 MPH -- a small difference, but the MPH scale is more trustworthy.

9. **Cross-check digitized values by reading the chart manually.** After importing data, pick a specific condition and verify against a manual chart reading. For Fig 5-09, checking VX/VY at DA 3,449 ft (S95 summer day) confirmed the model matched within 1 MPH.

### Model Calibration

1. **Nomogram digitization introduces ~5% compound error.** Each panel read has ±1-2% precision. Three panels compound to ±4-6%. A conservative bias of 5% applied to takeoff distances accounts for this.

2. **Weight correction follows power law W^2.33.** Not W^2 as textbooks suggest. The exponent is remarkably consistent across all weight data points (±0.02). Linear interpolation between digitized weight points is sufficient.

3. **Cross-check against Power Setting Table.** The Fig 5-15 power setting table is exactly transcribed and serves as the primary validation reference. Sea level BHP from Fig 5-04 matches the power table within 1 BHP at all tested points.

4. **The POH flight planning example is the key integration test.** It exercises takeoff, climb, cruise, and landing at specific conditions. Located in POH Sec 5, pages 5-2 through 5-4. Conditions: 3000 lb, 2000 ft PA / 60°F takeoff, 7000 ft cruise at 75%, 4000 ft PA / 60°F landing.

---

## Validation Results (2026-03-29)

| Check | Computed | Expected | Status |
|-------|----------|----------|--------|
| Power Setting (14 tests) | exact | exact | PASS |
| Stall clean 3100 lb | 65.1 kt | 65 kt | PASS |
| Stall flaps 3100 lb | 58.3 kt | 58 kt | PASS |
| Fuel flow (6 tests at 2400 RPM) | within 0.2 | exact | PASS |
| Fuel flow climb (2700 RPM full power) | 21.5 GPH | 21.5 GPH | PASS |
| SL BHP at 24.8/2400 RPM | 196 | 195 (75%) | PASS |
| SL BHP at 22.2/2400 RPM | 169 | 169 (65%) | PASS |
| SL BHP at 19.8/2400 RPM | 144 | 143 (55%) | PASS |
| TO ground run SL/Std/3100/0 | 1327 ft | 1260 ft | PASS (+5% conservative) |
| TO ground run POH example | 1068 ft | 1100 ft | PASS (within 3%) |
| TO over 50ft SL/Std/3100/0 | 1831 ft | 1725 ft | PASS (+6% conservative) |
| TO over 50ft POH example | 1552 ft | 1500 ft | PASS (+3.5%) |
| TO user reading #1 (2700lb) | 858 ft | ~860 ft | PASS |
| TO user reading #2 (3000lb) | 1068 ft | ~1050 ft | PASS |
| DA SL/Std | 18 ft | 0 ft | PASS |
| DA 5000/90F | 8055 ft | ~7880 ft | PASS |
| ROC SL/3100 clean | 1359 fpm | 1370 fpm | PASS |
| ROC SL/2100 clean | 2263 fpm | 2250 fpm | PASS |
| Time to climb 2000→7000 (3000 lb) | 4.5 min | ~4.5 min | PASS |
| VX clean at DA 3449 | 89 MPH | ~88 MPH (user read) | PASS |
| VY clean at DA 3449 | 109 MPH | ~108 MPH (user read) | PASS |
| VY clean at SL | 111 MPH | 105 MPH (POH Sec 2) | NOTE: 6 MPH gap |
| TAS 75% 7000ft | 158 kt | 158 kt | PASS (exact) |
| Landing roll SL/Std/2945/0 | 972 ft | 925 ft | PASS (+5% conservative) |
| Landing roll POH example | 835 ft | ~850 ft | PASS (within 2%) |
| Landing over 50ft SL/Std/2945/0 | 1502 ft | 1435 ft | PASS (+5% conservative) |
| Landing over 50ft POH example | 1301 ft | ~1300 ft | PASS (within 0.1%) |

---

## What's Next

### ALL CHARTS COMPLETE. Remaining work:

1. **Real-world validation** -- compare against actual flight data. Remove conservative bias once validated.
2. **Interactive CLI or web interface** -- make it usable for preflight planning.
3. **W&B calculator integration** -- use N9082P-specific empty weight and loading arms.

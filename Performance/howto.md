# How-To: Performance Digitization

## Digitization Workflow

1. **Export chart page** from `Manuals/N9082P-Performance.pdf` as 300 DPI PNG using the Swift/PDFKit script. PNGs already exported to `charts/`. Page index (0-based): page 7=Fig 5-02, page 8=5-03, page 9=5-04, page 10=5-05, page 11=5-06, page 12=5-07, page 13=5-08, page 14=5-09, page 15=5-10, page 16=5-11, page 17=5-12, page 18=5-13, page 19=5-14.

2. **Open WebPlotDigitizer** (https://automeris.io/WebPlotDigitizer/), load the PNG.

3. **Calibrate axes** for each panel. For multi-panel nomograms, use WebPlotDigitizer's multiple-axes feature -- each panel gets its own axis calibration.

4. **Create one dataset per curve.** Name datasets clearly (e.g., "2400 RPM - Best Economy Mixture", "Pressure Altitude FEET - 3000"). Don't mix multiple curves into one dataset.

5. **Trace curves** with dense points for curved lines (10-20+ points), fewer for straight lines (2 endpoints). Add more points in regions of high curvature.

6. **Export as JSON** to `charts/data/`. Naming convention: `Fig5-XX_Chart_Name.json`. For multi-panel charts with separate calibrations, add suffixes: `-SEA-LEVEL-PERFORMANCE.json`, `-knots.json`, etc.

7. **Give the JSON to the agent** with units for each axis. The agent parses the data, cross-checks against known values, updates the Python model, and runs validation tests.

## Chart Types and Approaches

### Simple X-Y Charts (Figs 5-02, 5-03, 5-05, 5-08, 5-09, 5-10, 5-11, 5-12)
- Single axis calibration
- One dataset per curve
- Stored as 1-D lookup tables with piecewise linear interpolation
- Some charts have straight lines (fuel consumption) -- only need 2 endpoints

### Multi-Panel Nomograms (Figs 5-06, 5-07, 5-13, 5-14)
- Three panels: Temperature/Altitude → Weight → Headwind/Distance
- Each panel needs its own axis calibration
- Panel 1: One dataset per altitude curve. X=Temperature, Y=Distance (right-side scale)
- Panel 2: Trace guide lines across weight ticks. 4+ guide lines at different heights, 5 weight ticks each
- Panel 3: Trace guide lines across headwind ticks. 4+ guide lines, calibrate on KNOTS scale (not MPH)
- **Important:** The chart has separate MPH and KNOTS scales at different positions. Always specify which was used.

### Tabular Data (Fig 5-15)
- Direct transcription from PDF text. No digitization tool needed.

### Three-Panel Engine Charts (Fig 5-04)
- Sea Level panel: X=MAP, Y=BHP. One line per RPM.
- Altitude panel: X=Altitude (kft), Y=BHP. RPM lines + MAP iso-lines.
- Temp panel: Standard lapse line.
- Three separate JSONs, one per panel.

## Key Units Conventions

- **Always specify units** with each JSON submission
- POH uses MPH natively, but knots preferred for output
- Headwind charts: calibrate on KNOTS scale if available
- Temperature: degrees Fahrenheit
- Altitude: feet (some charts use thousands of feet -- specify)
- Weight: pounds (some charts show LBS × 100)
- Distance: feet
- Fuel flow: US gallons per hour
- MAP: inches of mercury (in Hg)
- BHP: brake horsepower

## Validation

- Primary test: `python3 tests/test_validation.py` from the Performance directory
- POH flight planning example (Sec 5 p5-2 through 5-4) is the integration test
- Known reference values from Power Setting Table (exact) and POH Section 2 (stall speeds)
- All computed values should be conservative (overpredict distances, underpredict climb rates)
- The NWS density altitude formula is used: `DA = 145442.16 * (1 - (17.326 * P/T_R)^0.235)`

## Tools

- **Python 3** -- no external dependencies (pure Python, no numpy/scipy)
- **Swift/PDFKit** -- for extracting chart pages from PDF as images (macOS)
- **WebPlotDigitizer** -- browser-based chart digitization
- Custom interpolation utilities in `src/utils/interpolation.py`

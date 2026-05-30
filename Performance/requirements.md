# Requirements: Performance Digitization

## Functional
- Digitize all 14 performance charts from POH Section 5 (Figures 5-01 through 5-15) ✓ COMPLETE
- Accept standard flight inputs: pressure altitude, OAT, weight, headwind, surface type
- Return computed performance values matching POH charts within 1-2% accuracy
- Any residual error must be conservative (predict worse performance than POH)
- Output in knots as primary unit, with MPH available (POH native is MPH)
- Surface and slope corrections per POH Sec 5 p5-4
- Takeoff/landing distances include 5% conservative bias for nomogram compound error

## Non-Functional
- Pure Python 3, no external dependencies (no numpy/scipy required)
- All data embedded in source modules (no external data files)
- Each chart module independently usable
- Clear separation from authoritative POH data (per feedback_performance_separation.md)
- All outputs labeled as "EXPERIMENTAL -- digitized approximation"

## Data Sources
- WebPlotDigitizer JSON exports from N9082P-Performance.pdf (HQ scans, 300 DPI)
- POH Section 5 PDF text extraction (Power Setting Table -- complete tabular data)
- POH reference values from POH.md digest (stall speeds, SL distances, fuel flows)
- POH flight planning example (Sec 5 p5-2 through 5-4) as primary validation target
- Manual chart readings by pilot for cross-validation

## Validation
- All computed values compared against POH at reference points
- POH flight planning example used as integration test
- Manual chart readings used to cross-validate takeoff distances and VX/VY
- Test suite in tests/test_validation.py -- all PASS

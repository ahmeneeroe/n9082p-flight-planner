"""Figure 5-02: Airspeed Calibration (IAS to CAS)

Primary pitot-static system, standard pitot-static head.
Source: POH Section 5, page 5-6.
Digitized via WebPlotDigitizer (2026-03-29) from N9082P-Performance.pdf page 7.

Y-axis: IAS in knots. X-axis: correction in MPH.
CAS_MPH = IAS_MPH + correction_MPH

Two curves: Flaps Retracted (clean) and Flaps Fully Extended (32 deg + gear down).
Both were traced into a single dataset and separated by click order.
"""

from ..utils.interpolation import interp_1d
from ..utils.units import mph_to_knots, knots_to_mph

# ── Digitized from Figure 5-02 via WebPlotDigitizer ──
# Stored as IAS (MPH) → correction (MPH), where CAS = IAS + correction.
# Source data was IAS in knots, converted here to MPH (* 1/0.868976).

# Flaps Retracted (clean) -- 31 data points
IAS_CLEAN_MPH = [
    75.3, 78.5, 81.8, 85.0, 89.4, 93.0, 96.6, 100.2, 103.8, 109.5,
    115.1, 119.1, 123.9, 128.7, 132.7, 139.6, 146.4, 152.4, 156.4,
    160.8, 164.9, 170.9, 175.3, 180.1, 186.1, 191.8, 196.6, 201.0,
    209.0, 217.0, 226.7,
]
CAS_CORRECTION_CLEAN = [
    -0.8, -0.3, 0.1, 0.4, 0.8, 1.0, 1.2, 1.3, 1.4, 1.5,
    1.6, 1.6, 1.7, 1.7, 1.7, 1.6, 1.5, 1.3, 1.1,
    0.8, 0.5, 0.0, -0.4, -0.8, -1.2, -1.4, -1.6, -1.7,
    -1.9, -2.0, -2.1,
]

# Flaps Fully Extended (32 deg) + Gear Down -- 14 data points
IAS_FLAPS_MPH = [
    65.3, 72.5, 80.2, 85.8, 91.0, 95.8, 99.0, 103.4, 107.5, 110.7,
    113.5, 117.1, 121.1, 124.7,
]
CAS_CORRECTION_FLAPS = [
    -1.0, -1.2, -1.6, -2.1, -2.5, -2.8, -2.9, -2.9, -2.7, -2.4,
    -2.1, -1.5, -0.8, 0.0,
]


def ias_to_cas_mph(ias_mph: float, config: str = "clean") -> float:
    """Convert indicated airspeed to calibrated airspeed in MPH.

    Args:
        ias_mph: Indicated airspeed in MPH
        config: "clean" (flaps retracted) or "flaps_extended" (full flaps + gear)

    Returns:
        Calibrated airspeed in MPH.
    """
    if config == "clean":
        correction = interp_1d(ias_mph, IAS_CLEAN_MPH, CAS_CORRECTION_CLEAN)
    elif config == "flaps_extended":
        correction = interp_1d(ias_mph, IAS_FLAPS_MPH, CAS_CORRECTION_FLAPS)
    else:
        raise ValueError("config must be 'clean' or 'flaps_extended'")

    return round(ias_mph + correction, 1)


def ias_to_cas_knots(ias_knots: float, config: str = "clean") -> float:
    """Convert IAS to CAS in knots.

    Converts to MPH internally, applies correction, converts back.
    """
    ias_mph = knots_to_mph(ias_knots)
    cas_mph = ias_to_cas_mph(ias_mph, config)
    return round(mph_to_knots(cas_mph), 1)


def cas_to_ias_mph(cas_mph: float, config: str = "clean") -> float:
    """Convert calibrated airspeed to indicated airspeed in MPH.

    Inverse lookup -- iterative approach since correction depends on IAS.
    """
    ias = cas_mph
    for _ in range(10):
        cas_calc = ias_to_cas_mph(ias, config)
        error = cas_calc - cas_mph
        ias -= error
        if abs(error) < 0.1:
            break
    return round(ias, 1)

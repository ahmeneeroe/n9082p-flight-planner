"""Figures 5-13 & 5-14: Landing Distance

Landing ground roll and distance over 50 ft obstacle.
Source: POH Section 5, pages 5-17 and 5-18.

Figure 5-13 digitized via WebPlotDigitizer (2026-03-29) from
N9082P-Performance.pdf. Three-panel nomogram:
  - Panel 1: Temperature/Altitude → base distance (5 altitude curves)
  - Panel 2: Weight correction (8 guide lines)
  - Panel 3: Headwind correction in knots (7 guide lines)

Conditions: 32-deg flaps, paved/level/dry runway,
maximum braking effort, approach speed = 1.3 x Vso.
Maximum landing weight: 2945 lb (per chart note).

NOTE: For a standard (non-short-field) landing, the POH states
ground roll is approximately TWICE the charted distance.

Figure 5-14 (over 50 ft obstacle) digitized via WebPlotDigitizer (2026-03-29).
"""

from ..utils.interpolation import interp_1d

# ══════════════════════════════════════════════════════════════════════
# Figure 5-13: Landing Ground Roll Distance (Digitized)
# ══════════════════════════════════════════════════════════════════════

# ── Panel 1: Temperature/Altitude → Base Distance (max landing wt, no wind) ──

_PA_CURVES = {
    0: [
        (0.3, 818), (99.6, 1000),
    ],
    2000: [
        (-0.4, 886), (46.8, 969), (99.5, 1068),
    ],
    4000: [
        (-0.4, 951), (44.9, 1043), (69.5, 1089), (99.5, 1151),
    ],
    6000: [
        (-0.5, 1034), (19.8, 1071), (40.0, 1114), (59.6, 1157),
        (79.8, 1203), (99.5, 1249),
    ],
    8000: [
        (0.1, 1120), (19.7, 1160), (39.3, 1206), (59.6, 1255),
        (79.8, 1314), (99.4, 1382),
    ],
}

_ALTITUDES = sorted(_PA_CURVES.keys())


def _base_distance(oat_f: float, pressure_alt_ft: float) -> float:
    """Base landing ground roll at max landing weight, no wind, from Panel 1."""
    alt = max(_ALTITUDES[0], min(_ALTITUDES[-1], pressure_alt_ft))

    import bisect
    idx = bisect.bisect_right(_ALTITUDES, alt) - 1
    idx = min(idx, len(_ALTITUDES) - 2)

    alt_lo = _ALTITUDES[idx]
    alt_hi = _ALTITUDES[idx + 1]

    curve_lo = _PA_CURVES[alt_lo]
    curve_hi = _PA_CURVES[alt_hi]

    dist_lo = interp_1d(oat_f,
                        [p[0] for p in curve_lo],
                        [p[1] for p in curve_lo])
    dist_hi = interp_1d(oat_f,
                        [p[0] for p in curve_hi],
                        [p[1] for p in curve_hi])

    t = (alt - alt_lo) / (alt_hi - alt_lo) if alt_hi != alt_lo else 0.0
    return dist_lo + t * (dist_hi - dist_lo)


# ── Panel 2: Weight Correction ──
# Max landing weight ~2945 lb (chart reference line at ~2955).
# Factors derived from two 5-point guide lines, averaged.

WEIGHT_BREAKPOINTS = [2300, 2500, 2700, 2900, 2945]
WEIGHT_FACTORS = [0.775, 0.835, 0.905, 0.981, 1.000]


# ── Panel 3: Headwind Correction (knots) ──
# Multiplicative factors from middle-to-upper guide lines.
# Headwind calibrated in knots directly.

_HW_KT = [0.0, 8.7, 17.4, 26.2]
_HW_FACTORS = [1.000, 0.816, 0.632, 0.481]


def _apply_weight(base_dist: float, weight_lb: float) -> float:
    """Apply weight correction to base distance."""
    factor = interp_1d(weight_lb,
                       [float(w) for w in WEIGHT_BREAKPOINTS],
                       WEIGHT_FACTORS)
    return base_dist * factor


def _apply_headwind(dist: float, headwind_kt: float) -> float:
    """Apply headwind correction in knots. Negative = tailwind."""
    if headwind_kt >= 0:
        hw = min(headwind_kt, 26.0)
        factor = interp_1d(hw, [float(h) for h in _HW_KT], _HW_FACTORS)
        return max(0.0, dist * factor)
    else:
        tailwind_kt = abs(headwind_kt)
        return dist * (1.0 + 0.20 * tailwind_kt / 5.8)


# ── Surface correction factors (POH Sec 5 p5-4) ──
SURFACE_CORRECTIONS = {
    "paved_dry": 1.00,
    "dry_grass_short": 1.20,
    "dry_grass_tall": 1.30,
    "wet_grass_short": 1.30,
    "wet_grass_tall": 1.40,
    "soft_ground": 1.25,
}

SLOPE_FACTOR_PER_DEG = 0.05  # +10% per 2 deg downhill for landing

# Conservative bias (same rationale as takeoff)
CONSERVATIVE_BIAS = 1.05


def landing_ground_roll(pressure_alt_ft: float, oat_f: float,
                        weight_lb: float = 2945.0,
                        headwind_kt: float = 0.0,
                        surface: str = "paved_dry",
                        downhill_deg: float = 0.0) -> float:
    """Compute landing ground roll distance in feet.

    Per POH Figure 5-13 (digitized). Short-field technique
    (32-deg flaps, max braking, approach at 1.3 x Vso).

    NOTE: For a standard landing, ground roll ≈ TWICE charted distance.

    Args:
        pressure_alt_ft: Pressure altitude (feet)
        oat_f: Outside air temperature (degrees F)
        weight_lb: Aircraft weight (pounds), max 2945 for landing
        headwind_kt: Headwind component (knots). Negative = tailwind.
        surface: Surface type key from SURFACE_CORRECTIONS
        downhill_deg: Downhill runway slope in degrees

    Returns:
        Landing ground roll distance (feet). Short-field technique.
    """
    base = _base_distance(oat_f, pressure_alt_ft)
    dist = _apply_weight(base, weight_lb)
    dist = _apply_headwind(dist, headwind_kt)

    dist *= CONSERVATIVE_BIAS
    surf_factor = SURFACE_CORRECTIONS.get(surface, 1.0)
    slope_factor = 1.0 + SLOPE_FACTOR_PER_DEG * downhill_deg
    dist *= surf_factor * slope_factor

    return round(dist)


# ══════════════════════════════════════════════════════════════════════
# Figure 5-14: Landing Distance Over 50 ft Obstacle (Digitized)
# ══════════════════════════════════════════════════════════════════════

# Digitized via WebPlotDigitizer (2026-03-29). Three-panel nomogram.
# 32-deg flaps, max braking, approach at 1.3 x Vso.
# Max landing weight ~2945 lb.

# ── Panel 1: Temperature/Altitude → Base Distance ──
_OV50_PA_CURVES = {
    0: [(-0.6, 1317), (99.4, 1508)],
    1000: [(-0.6, 1354), (98.8, 1538)],
    2000: [(-0.6, 1391), (99.4, 1575)],
    3000: [(-0.6, 1431), (98.8, 1634)],
    4000: [(-0.6, 1465), (98.8, 1674)],
    5000: [(-0.6, 1498), (98.8, 1714)],
    6000: [(-0.6, 1535), (98.8, 1754)],
    7000: [(-0.6, 1572), (98.8, 1809)],
    8000: [(-0.6, 1615), (98.8, 1855)],
}

_OV50_ALTITUDES = sorted(_OV50_PA_CURVES.keys())

# ── Panel 2: Weight Correction ──
# 13 guidelines all show consistent factor ~0.855 at 2305 vs 2950 lb.
# Power law: factor = (W/2945)^0.635
_OV50_WEIGHT_BP = [2300, 2500, 2700, 2900, 2945]
_OV50_WEIGHT_FACTORS = [0.855, 0.901, 0.947, 0.990, 1.000]

# ── Panel 3: Headwind Correction (MPH, convert to knots) ──
# Calibration was correct for MPH (no ×10 needed).
# Factors from upper 3 guidelines.
_OV50_HW_KT = [0.0, 8.7, 17.4, 26.1]
_OV50_HW_FACTORS = [1.000, 0.829, 0.664, 0.539]


def _ov50_base_distance(oat_f: float, pressure_alt_ft: float) -> float:
    """Base landing over-50ft distance at max landing weight, no wind."""
    alt = max(_OV50_ALTITUDES[0], min(_OV50_ALTITUDES[-1], pressure_alt_ft))

    import bisect
    idx = bisect.bisect_right(_OV50_ALTITUDES, alt) - 1
    idx = min(idx, len(_OV50_ALTITUDES) - 2)

    alt_lo = _OV50_ALTITUDES[idx]
    alt_hi = _OV50_ALTITUDES[idx + 1]

    curve_lo = _OV50_PA_CURVES[alt_lo]
    curve_hi = _OV50_PA_CURVES[alt_hi]

    dist_lo = interp_1d(oat_f,
                        [p[0] for p in curve_lo],
                        [p[1] for p in curve_lo])
    dist_hi = interp_1d(oat_f,
                        [p[0] for p in curve_hi],
                        [p[1] for p in curve_hi])

    t = (alt - alt_lo) / (alt_hi - alt_lo) if alt_hi != alt_lo else 0.0
    return dist_lo + t * (dist_hi - dist_lo)


def landing_over_50ft(pressure_alt_ft: float, oat_f: float,
                      weight_lb: float = 2945.0,
                      headwind_kt: float = 0.0,
                      surface: str = "paved_dry",
                      downhill_deg: float = 0.0) -> float:
    """Compute landing distance over a 50-ft obstacle in feet.

    Per POH Figure 5-14 (digitized). Short-field technique
    (32-deg flaps, max braking, approach at 1.3 x Vso).

    Args:
        pressure_alt_ft: Pressure altitude (feet)
        oat_f: Outside air temperature (degrees F)
        weight_lb: Aircraft weight (pounds), max 2945
        headwind_kt: Headwind component (knots). Negative = tailwind.
        surface: Surface type key from SURFACE_CORRECTIONS
        downhill_deg: Downhill runway slope in degrees

    Returns:
        Landing distance over 50-ft obstacle (feet).
    """
    base = _ov50_base_distance(oat_f, pressure_alt_ft)

    wt_factor = interp_1d(weight_lb,
                          [float(w) for w in _OV50_WEIGHT_BP],
                          _OV50_WEIGHT_FACTORS)
    dist = base * wt_factor

    if headwind_kt >= 0:
        hw = min(headwind_kt, 26.0)
        hw_factor = interp_1d(hw,
                              [float(h) for h in _OV50_HW_KT],
                              _OV50_HW_FACTORS)
        dist = max(0.0, dist * hw_factor)
    else:
        tailwind_kt = abs(headwind_kt)
        dist *= (1.0 + 0.20 * tailwind_kt / 5.8)

    dist *= CONSERVATIVE_BIAS
    surf_factor = SURFACE_CORRECTIONS.get(surface, 1.0)
    slope_factor = 1.0 + SLOPE_FACTOR_PER_DEG * downhill_deg
    dist *= surf_factor * slope_factor

    return round(dist)

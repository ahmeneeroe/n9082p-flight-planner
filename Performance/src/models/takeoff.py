"""Figures 5-06 & 5-07: Takeoff Distance

Takeoff ground run and distance over 50 ft obstacle.
Source: POH Section 5, pages 5-10 and 5-11.

Figure 5-06 digitized via WebPlotDigitizer (2026-03-29) from
N9082P-Performance.pdf. Three-panel nomogram:
  - Panel 1: Temperature/Altitude → base distance (9 altitude curves)
  - Panel 2: Weight correction (4 guide lines digitized)
  - Panel 3: Headwind correction in MPH (4 guide lines digitized)

Conditions: 15-deg flaps, paved/level/dry runway,
full throttle, max RPM, takeoff speed = Vso (ground run)
or attain 1.3 x Vso at 50 ft (obstacle clearance).

Figure 5-07 (over 50 ft obstacle) also digitized as a separate
three-panel nomogram with its own altitude curves, weight guidelines,
and headwind guidelines. Weight correction is distance-dependent.
"""

from ..utils.interpolation import interp_1d

# ══════════════════════════════════════════════════════════════════════
# Figure 5-06: Takeoff Ground Run Distance (Digitized)
# ══════════════════════════════════════════════════════════════════════

# ── Panel 1: Temperature/Altitude → Base Distance (3100 lb, no wind) ──
# Each altitude has a list of (temperature_F, distance_ft) pairs sorted by temp.

_PA_CURVES = {
    0: [  # Sea Level
        (-0.3, 1060), (7.5, 1082), (15.9, 1104), (29.3, 1149),
        (39.4, 1188), (51.2, 1233), (65.2, 1288), (79.2, 1355),
        (88.7, 1400), (94.3, 1433), (99.3, 1456),
    ],
    1000: [
        (-0.3, 1127), (10.9, 1160), (24.9, 1205), (34.9, 1244),
        (43.3, 1277), (52.9, 1316), (64.1, 1367), (75.8, 1422),
        (87.6, 1489), (97.7, 1545),
    ],
    2000: [
        (-0.3, 1210), (10.3, 1244), (19.8, 1272), (29.9, 1311),
        (39.4, 1350), (49.5, 1394), (59.0, 1439), (68.0, 1484),
        (80.9, 1551), (91.5, 1612), (99.9, 1662),
    ],
    3000: [
        (-0.3, 1294), (11.5, 1339), (23.2, 1389), (33.3, 1433),
        (46.2, 1500), (57.9, 1562), (68.0, 1618), (74.7, 1657),
        (83.1, 1712), (92.1, 1774), (99.4, 1824),
    ],
    4000: [
        (-0.3, 1394), (6.4, 1422), (16.0, 1467), (25.5, 1517),
        (32.8, 1556), (40.0, 1595), (47.9, 1640), (52.9, 1668),
        (58.0, 1696), (62.4, 1724), (66.9, 1751), (72.0, 1785),
        (77.0, 1813), (82.6, 1852), (87.1, 1885), (90.5, 1908),
        (95.5, 1941), (100.0, 1969),
    ],
    5000: [
        (-0.3, 1528), (7.0, 1562), (14.9, 1601), (24.9, 1657),
        (31.1, 1684), (37.8, 1729), (46.8, 1779), (54.6, 1824),
        (62.5, 1874), (70.9, 1930), (78.7, 1980), (85.4, 2030),
        (93.3, 2086), (100.0, 2136),
    ],
    6000: [
        (-0.2, 1645), (10.4, 1701), (19.9, 1763), (29.5, 1824),
        (40.1, 1891), (49.1, 1952), (60.3, 2030), (72.0, 2114),
        (82.1, 2198), (91.1, 2265), (99.5, 2337),
    ],
    7000: [
        (-0.2, 1763), (10.4, 1824), (20.0, 1885), (28.4, 1941),
        (36.8, 1997), (42.9, 2041), (49.1, 2086), (54.7, 2125),
        (60.3, 2170), (64.8, 2209), (69.8, 2248), (74.9, 2287),
        (79.3, 2326), (84.4, 2371), (88.3, 2404), (93.9, 2454),
        (99.5, 2504),
    ],
    8000: [
        (-0.2, 1885), (12.1, 1963), (26.7, 2053), (35.1, 2120),
        (42.4, 2175), (50.2, 2237), (58.6, 2315), (66.5, 2382),
        (72.7, 2437), (78.8, 2499), (86.1, 2571), (91.7, 2633),
        (96.8, 2688), (99.6, 2716),
    ],
}

_ALTITUDES = sorted(_PA_CURVES.keys())


def _base_distance(oat_f: float, pressure_alt_ft: float) -> float:
    """Base takeoff ground run at 3100 lb, no wind, from Panel 1.

    Interpolates between altitude curves at the given temperature.
    """
    alt = max(_ALTITUDES[0], min(_ALTITUDES[-1], pressure_alt_ft))

    # Find bracketing altitudes
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


# ── Panel 2: Weight Correction (multiplicative factors) ──
# Derived from 4 digitized guide lines, averaged across guidelines.
# Factor = distance_at_weight / distance_at_3100

WEIGHT_BREAKPOINTS = [2300, 2500, 2700, 2900, 3100]
WEIGHT_FACTORS = [0.498, 0.607, 0.726, 0.856, 1.000]


# ── Panel 3: Headwind Correction (multiplicative, knots) ──
# Recalibrated in knots (2026-03-29). Chart has separate MPH/KNOTS
# scales. Tick marks at 10/20/30 MPH = 8.7/17.2/25.8 knots.
# Factors from upper 3 guide lines (lower excluded as outlier).

_HW_KT = [0.0, 8.7, 17.2, 25.8]
_HW_FACTORS = [1.000, 0.791, 0.580, 0.370]


def _apply_weight(base_dist: float, weight_lb: float) -> float:
    """Apply weight correction to base distance."""
    factor = interp_1d(weight_lb,
                       [float(w) for w in WEIGHT_BREAKPOINTS],
                       WEIGHT_FACTORS)
    return base_dist * factor


def _apply_headwind(dist: float, headwind_kt: float) -> float:
    """Apply headwind correction in knots.

    Calibrated from knots scale on chart. Negative = tailwind.
    """
    if headwind_kt >= 0:
        hw = min(headwind_kt, 26.0)
        factor = interp_1d(hw, [float(h) for h in _HW_KT], _HW_FACTORS)
        return max(0.0, dist * factor)
    else:
        # Tailwind: +20% per tailwind equal to 10% of liftoff speed (POH note)
        # Vso ≈ 58 kt, 10% ≈ 5.8 kt
        tailwind_kt = abs(headwind_kt)
        return dist * (1.0 + 0.20 * tailwind_kt / 5.8)


# ── Surface correction factors (POH Sec 5 p5-4) ──
SURFACE_CORRECTIONS = {
    "paved_dry": 1.00,
    "dry_grass_short": 1.20,
    "dry_grass_tall": 1.25,
    "wet_grass_short": 1.25,
    "wet_grass_tall": 1.30,
    "soft_ground": 1.25,
}

SLOPE_FACTOR_PER_DEG = 0.05  # +10% per 2 degrees uphill

# Conservative bias: digitized data reads ~5% optimistic vs POH example
# and manual chart readings. Accounts for nomogram reading precision
# compounding across three panels.
CONSERVATIVE_BIAS = 1.05


def takeoff_ground_run(pressure_alt_ft: float, oat_f: float,
                       weight_lb: float = 3100.0,
                       headwind_kt: float = 0.0,
                       surface: str = "paved_dry",
                       uphill_deg: float = 0.0) -> float:
    """Compute takeoff ground run distance in feet.

    Per POH Figure 5-06. Short-field technique (15-deg flaps).

    NOTE: For a standard (non-short-field) takeoff, the POH states
    ground run is approximately TWICE the charted distance.

    Args:
        pressure_alt_ft: Pressure altitude (feet)
        oat_f: Outside air temperature (degrees F)
        weight_lb: Aircraft weight (pounds), max 3100
        headwind_kt: Headwind component (knots), 0-30. Negative = tailwind.
        surface: Surface type key from SURFACE_CORRECTIONS
        uphill_deg: Uphill runway slope in degrees

    Returns:
        Takeoff ground run distance (feet). Short-field technique.
    """
    # Panel 1: base distance from temp/altitude
    base = _base_distance(oat_f, pressure_alt_ft)

    # Panel 2: weight correction
    dist = _apply_weight(base, weight_lb)

    # Panel 3: headwind correction (chart has shared MPH/KNOTS scale)
    dist = _apply_headwind(dist, headwind_kt)

    # Conservative bias + surface and slope corrections
    dist *= CONSERVATIVE_BIAS
    surf_factor = SURFACE_CORRECTIONS.get(surface, 1.0)
    slope_factor = 1.0 + SLOPE_FACTOR_PER_DEG * uphill_deg
    dist *= surf_factor * slope_factor

    return round(dist)


# ══════════════════════════════════════════════════════════════════════
# Figure 5-07: Takeoff Distance Over 50 ft Obstacle (Digitized)
# ══════════════════════════════════════════════════════════════════════

# Digitized via WebPlotDigitizer (2026-03-29). Three-panel nomogram.
# 15-deg flaps, paved/level/dry, full throttle, attain 1.3 x Vso at 50 ft.

# ── Panel 1: Temperature/Altitude → Base Distance (3100 lb, no wind) ──
_OV50_PA_CURVES = {
    0: [
        (0.0, 1369), (20.2, 1492), (39.7, 1615), (60.5, 1754),
        (80.0, 1877), (99.5, 2000),
    ],
    1000: [
        (0.0, 1492), (20.2, 1615), (40.3, 1754), (60.5, 1877),
        (80.0, 2000), (99.5, 2123),
    ],
    2000: [
        (0.0, 1615), (20.2, 1738), (39.7, 1862), (59.8, 2000),
        (79.4, 2154), (99.5, 2323),
    ],
    3000: [
        (0.6, 1754), (20.2, 1892), (40.3, 2062), (59.8, 2262),
        (80.6, 2477), (99.5, 2708),
    ],
    4000: [
        (0.6, 1877), (20.2, 2077), (40.3, 2308), (59.8, 2538),
        (80.0, 2815), (99.5, 3108),
    ],
    5000: [
        (0.6, 2000), (20.2, 2277), (40.3, 2585), (59.8, 2892),
        (80.0, 3231), (99.5, 3569),
    ],
    6000: [
        (0.0, 2246), (20.2, 2585), (40.3, 2954), (60.5, 3354),
        (80.6, 3769), (99.5, 4200),
    ],
    7000: [
        (0.6, 2508), (20.2, 2908), (39.7, 3354), (59.8, 3862),
        (80.0, 4508), (99.5, 5477),
    ],
    8000: [
        (0.0, 2831), (20.2, 3262), (40.3, 3831), (59.8, 4538),
        (80.0, 5508), (99.5, 7062),
    ],
}

_OV50_ALTITUDES = sorted(_OV50_PA_CURVES.keys())

# ── Panel 2: Weight Correction ──
# Weight factors from 4 five-point guidelines, averaged.
# NOTE: Over-50ft weight correction is more aggressive than ground run
# because climb segment degrades with weight.
_OV50_WEIGHT_BP = [2300, 2500, 2700, 2900, 3100]
_OV50_WEIGHT_FACTORS = [0.472, 0.581, 0.706, 0.846, 1.000]

# ── Panel 3: Headwind Correction (MPH, ×10 from calibration) ──
# Converted to knots. Factors from upper guidelines (base >2000 ft).
_OV50_HW_KT = [0.0, 8.7, 17.4, 26.1]
_OV50_HW_FACTORS = [1.000, 0.823, 0.671, 0.550]


def _ov50_base_distance(oat_f: float, pressure_alt_ft: float) -> float:
    """Base over-50ft distance at 3100 lb, no wind, from Panel 1."""
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


def takeoff_over_50ft(pressure_alt_ft: float, oat_f: float,
                      weight_lb: float = 3100.0,
                      headwind_kt: float = 0.0,
                      surface: str = "paved_dry",
                      uphill_deg: float = 0.0) -> float:
    """Compute takeoff distance over a 50-ft obstacle in feet.

    Per POH Figure 5-07 (digitized). Short-field technique (15-deg flaps),
    attain 1.3 x Vso at 50 feet.

    Args:
        pressure_alt_ft: Pressure altitude (feet)
        oat_f: Outside air temperature (degrees F)
        weight_lb: Aircraft weight (pounds), max 3100
        headwind_kt: Headwind component (knots). Negative = tailwind.
        surface: Surface type key from SURFACE_CORRECTIONS
        uphill_deg: Uphill runway slope in degrees

    Returns:
        Total takeoff distance to clear 50-ft obstacle (feet).
    """
    # Panel 1: base distance
    base = _ov50_base_distance(oat_f, pressure_alt_ft)

    # Panel 2: weight correction
    wt_factor = interp_1d(weight_lb,
                          [float(w) for w in _OV50_WEIGHT_BP],
                          _OV50_WEIGHT_FACTORS)
    dist = base * wt_factor

    # Panel 3: headwind correction
    if headwind_kt >= 0:
        hw = min(headwind_kt, 26.0)
        hw_factor = interp_1d(hw,
                              [float(h) for h in _OV50_HW_KT],
                              _OV50_HW_FACTORS)
        dist = max(0.0, dist * hw_factor)
    else:
        tailwind_kt = abs(headwind_kt)
        dist *= (1.0 + 0.20 * tailwind_kt / 5.8)

    # Conservative bias + surface/slope
    dist *= CONSERVATIVE_BIAS
    surf_factor = SURFACE_CORRECTIONS.get(surface, 1.0)
    slope_factor = 1.0 + SLOPE_FACTOR_PER_DEG * uphill_deg
    dist *= surf_factor * slope_factor

    return round(dist)


def min_runway_for_abort(takeoff_50ft_dist: float) -> float:
    """Minimum safe runway length for aborted takeoff.

    POH flight planning example: abort distance ≈ 2x ground run ≈ 1.5x over-50ft.
    """
    return round(takeoff_50ft_dist * 1.5)

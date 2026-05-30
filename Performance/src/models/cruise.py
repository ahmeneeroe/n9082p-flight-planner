"""Figures 5-04, 5-10, 5-11, 5-12: Cruise Performance

Altitude Performance, True Airspeed, Range, and Endurance profiles.
Source: POH Section 5, pages 5-8, 5-14, 5-15, 5-16.

Figure 5-04 digitized via WebPlotDigitizer (2026-03-29) from
N9082P-Performance.pdf. Three panels:
  - Sea Level Performance: MAP vs BHP per RPM
  - Altitude Performance: Pressure Alt vs BHP per RPM (full throttle)
    plus MAP iso-lines
  - Standard Altitude Temperature: lapse line for temp correction

Temperature correction per chart note: ±1% BHP per 6°C (10.8°F)
deviation from standard induction air temperature.
"""

from ..utils.interpolation import interp_1d
from ..utils.atmosphere import density_altitude, standard_temp_f
from ..utils.units import mph_to_knots

# ══════════════════════════════════════════════════════════════════════
# Figure 5-04: Altitude Performance Curve (Digitized)
# ══════════════════════════════════════════════════════════════════════

# ── Sea Level Performance Panel ──
# Each RPM: (MAP_low, BHP_low, MAP_high, BHP_high) -- straight lines
# X = Manifold Pressure (in Hg), Y = BHP at standard sea level

_SL_LINES = {
    1800: (18.51, 89.9, 24.98, 138.7),
    1900: (18.06, 91.6, 25.87, 155.7),
    2000: (18.06, 97.5, 26.60, 170.1),
    2100: (18.05, 103.9, 27.74, 190.9),
    2200: (18.05, 110.7, 28.97, 215.0),
    2300: (18.00, 117.9, 28.86, 226.5),
    2400: (18.00, 124.7, 28.76, 237.9),
    2500: (18.00, 130.6, 28.66, 246.4),
    2600: (17.99, 135.3, 28.56, 254.9),
    2700: (17.99, 139.5, 28.55, 263.4),
}

# Operational limits from sea level panel
# Limiting MAP for continuous operation: above this line, time-limited
_LIMITING_MAP_CONTINUOUS = (24.98, 138.7, 28.97, 215.0)
# Full throttle zero ram: above limiting MAP line
_FULL_THROTTLE_ZERO_RAM = (28.97, 215.0, 28.55, 263.4)

SL_RPMS = sorted(_SL_LINES.keys())

# ── Altitude Performance Panel ──
# RPM lines: full-throttle BHP vs altitude (thousands of feet)
# Each: (alt_low_kft, bhp_low_alt, alt_high_kft, bhp_high_alt)
# Note: "low alt" = low altitude number = HIGH BHP (sea level end)

_ALT_RPM_LINES = {
    1800: (-0.30, 139.1,  18.36, 89.9),
    1900: (-0.29, 153.1,  19.46, 89.9),
    2000: (-0.28, 170.1,  20.63, 89.9),
    2100: (-0.30, 191.3,  21.67, 89.9),
    2200: (-0.28, 215.0,  22.59, 89.9),
    2300: (-0.29, 226.9,  23.51, 89.9),
    2400: (-0.29, 237.9,  24.00, 91.2),
    2500: (-0.30, 246.8,  24.00, 94.5),
    2600: (-0.30, 255.3,  24.00, 97.5),
    2700: (-0.30, 263.0,  24.00, 100.5),
}

# MAP iso-lines on altitude panel: short segments showing where
# each MAP intersects the RPM grid at altitude.
# Each: (alt_kft_high_rpm, bhp_high_rpm, alt_kft_low_rpm, bhp_low_rpm)
_ALT_MAP_LINES = {
    28: (0.50, 257.5, 1.07, 200.6),
    26: (3.08, 240.1, 3.54, 175.2),
    24: (5.48, 223.9, 6.43, 145.9),
    22: (8.06, 207.0, 8.89, 131.0),
    20: (10.89, 187.9, 11.54, 119.6),
    18: (13.60, 169.6, 14.18, 108.1),
    16: (16.37, 151.0, 16.76, 96.7),
    14: (19.20, 132.3, 19.83, 89.9),
    12: (22.27, 111.9, 22.59, 89.9),
}

# ── Standard Altitude Temperature Panel ──
# Lapse line: altitude (kft) → standard temp (F)
_STD_TEMP_LINE = (1.0, 60.6, 24.0, -24.5)

# Temperature correction: ±1% BHP per 10.8°F from standard
TEMP_CORRECTION_PER_F = 1.0 / 10.8 / 100.0  # fraction per degree F


def _interp_line(x: float, x1: float, y1: float, x2: float, y2: float) -> float:
    """Interpolate along a 2-point line, clamped to endpoints."""
    if x2 == x1:
        return y1
    t = max(0.0, min(1.0, (x - x1) / (x2 - x1)))
    return y1 + t * (y2 - y1)


def sea_level_bhp(map_inhg: float, rpm: int) -> float:
    """BHP at sea level for a given MAP and RPM.

    From digitized Sea Level Performance panel (Fig 5-04).

    Args:
        map_inhg: Manifold pressure in inches Hg
        rpm: Engine RPM (1800-2700)

    Returns:
        Brake horsepower at standard sea level conditions.
    """
    rpms = SL_RPMS
    rpm_f = float(max(rpms[0], min(rpms[-1], rpm)))

    # Find bracketing RPM lines
    import bisect
    idx = bisect.bisect_right(rpms, rpm_f) - 1
    idx = min(idx, len(rpms) - 2)

    rpm_lo, rpm_hi = rpms[idx], rpms[idx + 1]
    line_lo = _SL_LINES[rpm_lo]
    line_hi = _SL_LINES[rpm_hi]

    bhp_lo = _interp_line(map_inhg, line_lo[0], line_lo[1], line_lo[2], line_lo[3])
    bhp_hi = _interp_line(map_inhg, line_hi[0], line_hi[1], line_hi[2], line_hi[3])

    t = (rpm_f - rpm_lo) / (rpm_hi - rpm_lo) if rpm_hi != rpm_lo else 0.0
    return round(bhp_lo + t * (bhp_hi - bhp_lo), 1)


def full_throttle_bhp(pressure_alt_ft: float, rpm: int) -> float:
    """Maximum BHP available at full throttle.

    From digitized Altitude Performance RPM lines (Fig 5-04).

    Args:
        pressure_alt_ft: Pressure altitude in feet
        rpm: Engine RPM (1800-2700)

    Returns:
        Maximum BHP at full throttle, standard temperature.
    """
    alt_kft = pressure_alt_ft / 1000.0
    rpms = sorted(_ALT_RPM_LINES.keys())
    rpm_f = float(max(rpms[0], min(rpms[-1], rpm)))

    import bisect
    idx = bisect.bisect_right(rpms, rpm_f) - 1
    idx = min(idx, len(rpms) - 2)

    rpm_lo, rpm_hi = rpms[idx], rpms[idx + 1]
    line_lo = _ALT_RPM_LINES[rpm_lo]
    line_hi = _ALT_RPM_LINES[rpm_hi]

    bhp_lo = _interp_line(alt_kft, line_lo[0], line_lo[1], line_lo[2], line_lo[3])
    bhp_hi = _interp_line(alt_kft, line_hi[0], line_hi[1], line_hi[2], line_hi[3])

    t = (rpm_f - rpm_lo) / (rpm_hi - rpm_lo) if rpm_hi != rpm_lo else 0.0
    return round(max(0.0, bhp_lo + t * (bhp_hi - bhp_lo)), 1)


def max_map_at_altitude(pressure_alt_ft: float) -> float:
    """Approximate max available MAP at full throttle.

    Derived from MAP iso-lines on altitude panel. For a normally
    aspirated engine, full-throttle MAP drops ~1 in Hg per 1,000 ft.

    Args:
        pressure_alt_ft: Pressure altitude in feet

    Returns:
        Maximum manifold pressure in inches Hg.
    """
    # Use the MAP iso-lines: each MAP value is associated with an
    # altitude where it becomes the full-throttle limit
    maps = sorted(_ALT_MAP_LINES.keys(), reverse=True)
    alts_kft = []
    for m in maps:
        line = _ALT_MAP_LINES[m]
        avg_alt = (line[0] + line[2]) / 2.0
        alts_kft.append(avg_alt)

    alt_kft = pressure_alt_ft / 1000.0
    return round(interp_1d(alt_kft,
                           alts_kft,
                           [float(m) for m in maps]), 1)


def bhp_at_altitude(pressure_alt_ft: float, rpm: int,
                    map_inhg: float, oat_f: float = None) -> float:
    """Actual BHP at altitude for given MAP, RPM, and temperature.

    For a fuel-injected engine, BHP at a given MAP and RPM is nearly
    the same at altitude as at sea level (MAP is absolute pressure).
    The main corrections are:
    - Cannot exceed full-throttle BHP at altitude
    - Temperature correction: ±1% per 10.8°F from standard

    Args:
        pressure_alt_ft: Pressure altitude in feet
        rpm: Engine RPM
        map_inhg: Manifold pressure in inches Hg
        oat_f: Outside air temperature in °F (None = standard)

    Returns:
        Actual brake horsepower.
    """
    # Sea level BHP at this MAP and RPM
    bhp = sea_level_bhp(map_inhg, rpm)

    # Cap at full-throttle maximum for this altitude and RPM
    ft_bhp = full_throttle_bhp(pressure_alt_ft, rpm)
    bhp = min(bhp, ft_bhp)

    # Temperature correction
    if oat_f is not None:
        std_temp = standard_temp_f(pressure_alt_ft)
        temp_delta = oat_f - std_temp
        bhp *= (1.0 - TEMP_CORRECTION_PER_F * temp_delta)

    return round(max(0.0, bhp), 1)


def max_bhp_at_altitude(pressure_alt_ft: float, rpm: int = 2700) -> float:
    """Maximum available BHP at full throttle (alias for full_throttle_bhp)."""
    return full_throttle_bhp(pressure_alt_ft, rpm)


# ══════════════════════════════════════════════════════════════════════
# Figure 5-10: True Airspeed vs Density Altitude (Digitized)
# ══════════════════════════════════════════════════════════════════════

# Digitized via WebPlotDigitizer (2026-03-29). X = TAS (knots), Y = DA (ft).
# 4 power-setting lines (straight, 2 pts each) + 2 full-throttle curves.
# Best power mixture, 3100 lb.

# Power lines: (da_low, tas_kt_low, da_high, tas_kt_high)
# TAS increases with altitude at constant power (TAS = CAS / sqrt(sigma))
_TAS_POWER_LINES = {
    45: (29, 115.5, 15996, 120.3),
    55: (21, 129.9, 15398, 141.6),
    65: (14, 140.0, 10775, 153.0),
    75: (9, 148.7, 6988, 158.1),
}

# Full-throttle curves (densely traced) -- TAS declines as power drops
_TAS_FT_2400 = [
    (6988, 158.1), (7357, 157.7), (7665, 157.4), (8035, 157.0),
    (8373, 156.6), (8620, 156.3), (9020, 155.8), (9420, 155.3),
    (9697, 154.9), (10067, 154.4), (10437, 153.8), (10899, 152.9),
    (11176, 152.5), (11484, 151.8), (11823, 151.2), (12192, 150.5),
    (12470, 149.8), (12839, 149.1), (13209, 148.1), (13487, 147.3),
    (13795, 146.5), (14041, 145.9), (14380, 144.9), (14720, 143.9),
    (15059, 142.8), (15398, 141.7),
]

_TAS_FT_2700 = [
    (27, 168.8), (458, 168.8), (1074, 168.7), (1474, 168.6),
    (1935, 168.4), (2397, 168.3), (2797, 168.2), (3197, 168.0),
    (3474, 167.9), (3813, 167.8), (4151, 167.5), (4428, 167.4),
    (4736, 167.3), (5013, 167.0), (5382, 166.9), (5690, 166.6),
    (6121, 166.3), (6614, 165.8), (7075, 165.5), (7537, 165.0),
    (8122, 164.5), (8523, 163.9), (9015, 163.4), (9477, 162.8),
    (9970, 162.1), (10339, 161.6), (10801, 160.9), (11263, 160.1),
    (11910, 158.9), (12342, 158.0), (12865, 156.9), (13358, 155.7),
    (13821, 154.7), (14252, 153.5), (14684, 152.3), (15115, 150.9),
    (15516, 149.6), (15979, 147.9),
]

_POWER_LEVELS = sorted(_TAS_POWER_LINES.keys())


def true_airspeed_knots(pressure_alt_ft: float, oat_f: float,
                        percent_power: float) -> float | None:
    """Compute true airspeed in knots at given conditions.

    Per POH Figure 5-10 (digitized). Best power mixture, 3100 lb.

    Args:
        pressure_alt_ft: Pressure altitude (feet)
        oat_f: Outside air temperature (degrees F)
        percent_power: Power setting (45-75%)

    Returns:
        TAS in knots, or None if power not available at that altitude.
    """
    da = density_altitude(pressure_alt_ft, oat_f)
    percent_power = max(45, min(75, percent_power))

    import bisect
    idx = bisect.bisect_right(_POWER_LEVELS, percent_power) - 1
    idx = min(idx, len(_POWER_LEVELS) - 2)

    p_low = _POWER_LEVELS[idx]
    p_high = _POWER_LEVELS[idx + 1]

    def tas_from_power_line(pwr):
        line = _TAS_POWER_LINES[pwr]
        da_lo, tas_lo, da_hi, tas_hi = line
        if da > da_hi + 100:  # 100 ft tolerance for DA formula offset
            return None  # power not available at this altitude
        da_clamped = min(da, da_hi)
        if da_clamped < da_lo:
            return tas_lo
        return tas_lo + (da_clamped - da_lo) / (da_hi - da_lo) * (tas_hi - tas_lo)

    tas_low = tas_from_power_line(p_low)
    tas_high = tas_from_power_line(p_high)

    if tas_low is None and tas_high is None:
        return None
    if tas_high is None:
        return round(tas_low)
    if tas_low is None:
        return None

    t = (percent_power - p_low) / (p_high - p_low)
    return round(tas_low + t * (tas_high - tas_low))


def true_airspeed_mph(pressure_alt_ft: float, oat_f: float,
                      percent_power: float) -> float | None:
    """Compute TAS in MPH."""
    tas = true_airspeed_knots(pressure_alt_ft, oat_f, percent_power)
    if tas is None:
        return None
    from ..utils.units import knots_to_mph
    return round(knots_to_mph(tas))


def full_throttle_tas_knots(pressure_alt_ft: float, oat_f: float,
                            rpm: int = 2700) -> float:
    """TAS at full throttle for a given altitude and RPM.

    From densely-traced full-throttle curves on Fig 5-10.

    Args:
        pressure_alt_ft: Pressure altitude (feet)
        oat_f: Outside air temperature (degrees F)
        rpm: 2400 or 2700

    Returns:
        TAS in knots at full throttle.
    """
    da = density_altitude(pressure_alt_ft, oat_f)

    if rpm <= 2400:
        curve = _TAS_FT_2400
    else:
        curve = _TAS_FT_2700

    das = [p[0] for p in curve]
    tass = [p[1] for p in curve]
    return round(interp_1d(da, [float(d) for d in das],
                           [float(t) for t in tass]), 1)


# ══════════════════════════════════════════════════════════════════════
# Figure 5-11: Range Profile (Digitized)
# ══════════════════════════════════════════════════════════════════════

# Digitized via WebPlotDigitizer (2026-03-29). X = Range (NM), Y = DA (ft).
# Best economy mixture, 3100 lb start weight.
# Includes start/taxi/takeoff/climb/descent + 45 min reserve.
# Range increases slightly with altitude (less drag at same TAS).
# Each line: (da_low, range_nm_low, da_high, range_nm_high)

_RANGE_56GAL = {
    55: (0, 594, 15386, 654),
    65: (0, 587, 10810, 629),
    75: (0, 560, 7002, 588),
}

_RANGE_86GAL = {
    55: (0, 949, 15263, 1008),
    65: (0, 921, 10749, 965),
    75: (0, 877, 7002, 904),
}


def range_nm(percent_power: float, fuel_gal: float = 86.0,
             pressure_alt_ft: float = 0.0, oat_f: float = 59.0) -> float:
    """Compute still-air range in nautical miles.

    Per POH Figure 5-11 (digitized). Best economy mixture, 3100 lb.
    Includes start/taxi/takeoff/climb/descent + 45 min reserve.

    Args:
        percent_power: Cruise power (55-75%)
        fuel_gal: Total fuel load (56 or 86 gallons, interpolates between)
        pressure_alt_ft: Pressure altitude (feet) for altitude correction
        oat_f: OAT in degrees F

    Returns:
        Range in nautical miles.
    """
    da = density_altitude(pressure_alt_ft, oat_f)
    percent_power = max(55, min(75, percent_power))

    def range_from_table(table):
        powers = sorted(table.keys())
        import bisect
        idx = bisect.bisect_right(powers, percent_power) - 1
        idx = min(idx, len(powers) - 2)
        p_lo, p_hi = powers[idx], powers[idx + 1]

        def interp_line(pwr):
            da_lo, r_lo, da_hi, r_hi = table[pwr]
            da_c = max(da_lo, min(da_hi, da))
            return r_lo + (da_c - da_lo) / (da_hi - da_lo) * (r_hi - r_lo) if da_hi != da_lo else r_lo

        r_lo = interp_line(p_lo)
        r_hi = interp_line(p_hi)
        t = (percent_power - p_lo) / (p_hi - p_lo) if p_hi != p_lo else 0.0
        return r_lo + t * (r_hi - r_lo)

    if fuel_gal >= 86:
        return round(range_from_table(_RANGE_86GAL))
    elif fuel_gal <= 56:
        return round(range_from_table(_RANGE_56GAL))
    else:
        r86 = range_from_table(_RANGE_86GAL)
        r56 = range_from_table(_RANGE_56GAL)
        t = (fuel_gal - 56.0) / 30.0
        return round(r56 + t * (r86 - r56))


def range_sm(percent_power: float, fuel_gal: float = 86.0,
             pressure_alt_ft: float = 0.0, oat_f: float = 59.0) -> float:
    """Compute still-air range in statute miles."""
    from ..utils.units import nm_to_sm
    return round(nm_to_sm(range_nm(percent_power, fuel_gal,
                                   pressure_alt_ft, oat_f)))


# ══════════════════════════════════════════════════════════════════════
# Figure 5-12: Endurance Profile (Digitized)
# ══════════════════════════════════════════════════════════════════════

# Digitized via WebPlotDigitizer (2026-03-29). X = Endurance (hrs), Y = DA (ft).
# 86 gal, best economy, 3100 lb.
# Includes start/taxi/takeoff/climb/descent + 45 min reserve.
# Endurance decreases slightly with altitude.
# Each line: (da_low, hrs_low, da_high, hrs_high)

_ENDURANCE_LINES = {
    45: (0, 7.9, 15015, 7.5),
    55: (0, 7.1, 14000, 6.7),
    65: (0, 6.3, 10000, 6.0),
    75: (0, 5.7, 6954, 5.5),
}


def endurance_hrs(percent_power: float,
                  pressure_alt_ft: float = 0.0,
                  oat_f: float = 59.0) -> float:
    """Compute endurance in hours.

    Per POH Figure 5-12 (digitized). 86 gal, best economy, 3100 lb.
    Includes start/taxi/takeoff/climb/descent + 45 min reserve.

    Args:
        percent_power: Cruise power (45-75%)
        pressure_alt_ft: Pressure altitude (feet)
        oat_f: OAT in degrees F

    Returns:
        Endurance in hours.
    """
    da = density_altitude(pressure_alt_ft, oat_f)
    percent_power = max(45, min(75, percent_power))

    powers = sorted(_ENDURANCE_LINES.keys())

    import bisect
    idx = bisect.bisect_right(powers, percent_power) - 1
    idx = min(idx, len(powers) - 2)

    p_lo, p_hi = powers[idx], powers[idx + 1]

    def interp_line(pwr):
        da_lo, h_lo, da_hi, h_hi = _ENDURANCE_LINES[pwr]
        da_c = max(da_lo, min(da_hi, da))
        return h_lo + (da_c - da_lo) / (da_hi - da_lo) * (h_hi - h_lo) if da_hi != da_lo else h_lo

    h_lo = interp_line(p_lo)
    h_hi = interp_line(p_hi)
    t = (percent_power - p_lo) / (p_hi - p_lo) if p_hi != p_lo else 0.0
    return round(h_lo + t * (h_hi - h_lo), 1)

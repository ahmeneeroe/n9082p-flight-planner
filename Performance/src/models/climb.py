"""Figures 5-08 & 5-09: Rate of Climb and VX/VY

Rate of climb vs density altitude, and best angle/rate speeds.
Source: POH Section 5, pages 5-12 and 5-13.

Figure 5-08 digitized via WebPlotDigitizer (2026-03-29) from
N9082P-Performance.pdf. X = ROC (fpm), Y = Density Altitude (ft).
All curves are straight lines (2 endpoints) -- ROC decreases linearly
with density altitude for normally aspirated engines.

5 datasets: 4 weight curves clean + 1 gear-down/flaps-15.

Figure 5-09 digitized via WebPlotDigitizer (2026-03-29) from MPH scale.
"""

from ..utils.interpolation import interp_1d
from ..utils.atmosphere import density_altitude, standard_temp_f
from ..utils.units import mph_to_knots

# ══════════════════════════════════════════════════════════════════════
# Figure 5-08: Rate of Climb vs Density Altitude (Digitized)
# ══════════════════════════════════════════════════════════════════════

# Each curve is a straight line: ROC = ROC_SL * (1 - DA / ceiling_DA)
# Stored as (ROC_at_SL, ceiling_DA) per weight/config.
# ROC_at_SL = fpm at density altitude 0
# ceiling_DA = density altitude where ROC = 0

# Clean configuration (gear up, flaps up)
_CLEAN_CURVES = {
    # weight_lb: (roc_sl_fpm, ceiling_da_ft)
    2100: (2265, 23947),
    2500: (1815, 22965),
    2900: (1495, 21982),
    3100: (1360, 20939),
}

# Gear extended, flaps 15 deg (initial climb after short-field takeoff)
_GEAR_DOWN_CURVE = (966, 15965)  # (roc_sl, ceiling_da) at 3100 lb

_CLEAN_WEIGHTS = sorted(_CLEAN_CURVES.keys())


def _roc_from_line(da: float, roc_sl: float, ceiling: float) -> float:
    """ROC from a linear decline line."""
    if da >= ceiling:
        return 0.0
    if da <= 0:
        return roc_sl
    return roc_sl * (1.0 - da / ceiling)


def rate_of_climb(pressure_alt_ft: float, oat_f: float,
                  config: str = "clean",
                  weight_lb: float = 3100.0) -> float:
    """Compute maximum rate of climb.

    Per POH Figure 5-08. Full throttle, max RPM, optimum airspeed.

    Args:
        pressure_alt_ft: Pressure altitude (feet)
        oat_f: Outside air temperature (degrees F)
        config: "clean" (gear up, flaps up) or "gear_down" (gear down, 15-deg flaps)
        weight_lb: Aircraft weight (pounds, 2100-3100)

    Returns:
        Rate of climb in ft/min. Returns 0 if above service ceiling.
    """
    da = density_altitude(pressure_alt_ft, oat_f)

    if config == "gear_down":
        # Only have data at 3100 lb for gear-down
        roc_sl, ceiling = _GEAR_DOWN_CURVE
        return round(max(0.0, _roc_from_line(da, roc_sl, ceiling)))

    if config != "clean":
        raise ValueError("config must be 'clean' or 'gear_down'")

    # Interpolate between weight curves
    wt = max(_CLEAN_WEIGHTS[0], min(_CLEAN_WEIGHTS[-1], weight_lb))

    import bisect
    idx = bisect.bisect_right(_CLEAN_WEIGHTS, wt) - 1
    idx = min(idx, len(_CLEAN_WEIGHTS) - 2)

    wt_lo = _CLEAN_WEIGHTS[idx]
    wt_hi = _CLEAN_WEIGHTS[idx + 1]

    roc_lo = _roc_from_line(da, *_CLEAN_CURVES[wt_lo])
    roc_hi = _roc_from_line(da, *_CLEAN_CURVES[wt_hi])

    t = (wt - wt_lo) / (wt_hi - wt_lo) if wt_hi != wt_lo else 0.0
    roc = roc_lo + t * (roc_hi - roc_lo)

    return round(max(0.0, roc))


def service_ceiling(weight_lb: float = 3100.0, config: str = "clean") -> float:
    """Density altitude where ROC = 100 fpm (service ceiling definition).

    Args:
        weight_lb: Aircraft weight (pounds)
        config: "clean" or "gear_down"

    Returns:
        Service ceiling in feet (density altitude).
    """
    if config == "gear_down":
        roc_sl, ceiling = _GEAR_DOWN_CURVE
        # DA where ROC = 100: 100 = roc_sl * (1 - DA/ceiling)
        return round(ceiling * (1.0 - 100.0 / roc_sl))

    wt = max(_CLEAN_WEIGHTS[0], min(_CLEAN_WEIGHTS[-1], weight_lb))

    import bisect
    idx = bisect.bisect_right(_CLEAN_WEIGHTS, wt) - 1
    idx = min(idx, len(_CLEAN_WEIGHTS) - 2)

    wt_lo = _CLEAN_WEIGHTS[idx]
    wt_hi = _CLEAN_WEIGHTS[idx + 1]

    ceil_lo = _CLEAN_CURVES[wt_lo][1] * (1.0 - 100.0 / _CLEAN_CURVES[wt_lo][0])
    ceil_hi = _CLEAN_CURVES[wt_hi][1] * (1.0 - 100.0 / _CLEAN_CURVES[wt_hi][0])

    t = (wt - wt_lo) / (wt_hi - wt_lo) if wt_hi != wt_lo else 0.0
    return round(ceil_lo + t * (ceil_hi - ceil_lo))


def time_to_climb(from_alt_ft: float, to_alt_ft: float,
                  oat_f: float = None,
                  config: str = "clean",
                  weight_lb: float = 3100.0) -> float:
    """Estimate time to climb between two altitudes.

    Uses average rate of climb between altitudes. If oat_f is None,
    assumes standard temperature at each altitude.

    Args:
        from_alt_ft: Starting pressure altitude (feet)
        to_alt_ft: Target pressure altitude (feet)
        oat_f: OAT in degrees F (optional, uses standard if None)
        config: "clean" or "gear_down"
        weight_lb: Aircraft weight (pounds)

    Returns:
        Estimated time to climb in minutes.
    """
    if to_alt_ft <= from_alt_ft:
        return 0.0

    # Integrate in 500-ft steps
    total_time_min = 0.0
    alt = from_alt_ft
    step = 500.0

    while alt < to_alt_ft:
        next_alt = min(alt + step, to_alt_ft)
        mid_alt = (alt + next_alt) / 2.0

        if oat_f is not None:
            temp = oat_f
        else:
            temp = standard_temp_f(mid_alt)

        roc = rate_of_climb(mid_alt, temp, config, weight_lb)
        if roc <= 0:
            return float('inf')

        delta_alt = next_alt - alt
        total_time_min += delta_alt / roc

        alt = next_alt

    return round(total_time_min, 1)


# ══════════════════════════════════════════════════════════════════════
# Figure 5-09: VX and VY vs Density Altitude (Digitized)
# ══════════════════════════════════════════════════════════════════════

# Digitized via WebPlotDigitizer (2026-03-29) from N9082P-Performance.pdf.
# X = Airspeed (MPH), Y = Density Altitude (ft).
# All curves are straight lines (2 endpoints).
#
# NOTE: VY retracted at SL = 110.9 MPH. POH Section 2 says 105 MPH.
# Discrepancy of ~6 MPH may be calibration precision on the 80-110 MPH
# axis range. Relative behavior (slopes, convergence) is correct.
#
# Stored as (speed_mph_at_SL, speed_mph_at_ceiling, ceiling_da_ft)

_VX_CLEAN = (86.8, 94.3, 15000)   # increases with altitude
_VY_CLEAN = (110.9, 100.9, 15000)  # decreases with altitude

_VX_GEAR_DOWN = (76.6, 80.3, 11988)
_VY_GEAR_DOWN = (96.3, 86.2, 11988)


def _speed_from_line(da: float, spd_sl: float, spd_ceil: float, ceiling: float) -> float:
    """Interpolate speed along a linear VX or VY line."""
    if da <= 0:
        return spd_sl
    if da >= ceiling:
        return spd_ceil
    t = da / ceiling
    return spd_sl + t * (spd_ceil - spd_sl)


def vx_mph(pressure_alt_ft: float, oat_f: float,
           config: str = "clean") -> float:
    """Best angle of climb speed (VX) in MPH.

    Per POH Figure 5-09 (digitized).
    """
    da = density_altitude(pressure_alt_ft, oat_f)

    if config == "clean":
        return round(_speed_from_line(da, *_VX_CLEAN))
    elif config == "gear_down":
        return round(_speed_from_line(da, *_VX_GEAR_DOWN))
    else:
        raise ValueError("config must be 'clean' or 'gear_down'")


def vy_mph(pressure_alt_ft: float, oat_f: float,
           config: str = "clean") -> float:
    """Best rate of climb speed (VY) in MPH.

    Per POH Figure 5-09 (digitized).
    NOTE: VY retracted at SL reads ~111 MPH; POH Sec 2 says 105 MPH.
    """
    da = density_altitude(pressure_alt_ft, oat_f)

    if config == "clean":
        return round(_speed_from_line(da, *_VY_CLEAN))
    elif config == "gear_down":
        return round(_speed_from_line(da, *_VY_GEAR_DOWN))
    else:
        raise ValueError("config must be 'clean' or 'gear_down'")


def vx_knots(pressure_alt_ft: float, oat_f: float,
             config: str = "clean") -> float:
    """Best angle of climb speed (VX) in knots."""
    return round(mph_to_knots(vx_mph(pressure_alt_ft, oat_f, config)))


def vy_knots(pressure_alt_ft: float, oat_f: float,
             config: str = "clean") -> float:
    """Best rate of climb speed (VY) in knots."""
    return round(mph_to_knots(vy_mph(pressure_alt_ft, oat_f, config)))

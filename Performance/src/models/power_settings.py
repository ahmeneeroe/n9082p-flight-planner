"""Figure 5-15: Power Setting Table

Lycoming IO-540-D, 260 HP normally aspirated engine.
Source: POH Section 5, page 5-19.

EXPERIMENTAL -- digitized approximation. Not validated.

Provides:
    - Required manifold pressure for a given altitude, RPM, and desired power %
    - Fuel flow at a given power % and mixture setting

Temperature correction: +0.17 in Hg per 10F above standard temp at altitude;
subtract for below standard.

Fuel consumption:
    Best economy (peak EGT) / Best power (100F rich of peak EGT)
    55%: 11.4 / 13.5 GPH
    65%: 12.7 / 15.0 GPH
    75%: 14.1 / 16.5 GPH
"""

from ..utils.interpolation import interp_1d, interp_2d_with_none
from ..utils.atmosphere import standard_temp_f

# ── Pressure altitudes (rows) ──
ALTITUDES = [0, 1000, 2000, 3000, 4000, 5000, 6000, 7000, 8000, 9000,
             10000, 11000, 12000, 13000, 14000, 15000]

# ── Standard temperatures at each altitude (F) ──
STD_TEMPS_F = [59, 55, 52, 48, 45, 41, 38, 34, 31, 27, 23, 19, 16, 12, 9, 5]

# ══════════════════════════════════════════════════════════════════════
# 55% RATED (143 HP)
# Fuel: 11.4 GPH best economy, 13.5 GPH best power
# RPM options: 2100, 2200, 2300, 2400
# ══════════════════════════════════════════════════════════════════════
RPMS_55 = [2100, 2200, 2300, 2400]

# MAP_55[alt_idx][rpm_idx] -- None means beyond full-throttle capability
MAP_55 = [
    # 2100   2200   2300   2400     altitude
    [22.3,  21.5,  20.7,  19.8],  # SL
    [22.1,  21.3,  20.5,  19.6],  # 1000
    [21.9,  21.0,  20.3,  19.4],  # 2000
    [21.7,  20.8,  20.0,  19.2],  # 3000
    [21.4,  20.6,  19.8,  19.0],  # 4000
    [21.2,  20.3,  19.6,  18.8],  # 5000
    [21.0,  20.1,  19.4,  18.6],  # 6000
    [20.7,  19.9,  19.1,  18.4],  # 7000
    [20.5,  19.6,  18.9,  18.2],  # 8000
    [20.3,  19.4,  18.7,  18.0],  # 9000
    [20.0,  19.2,  18.5,  17.7],  # 10000
    [19.8,  18.9,  18.2,  17.5],  # 11000
    [19.6,  18.7,  18.0,  17.3],  # 12000
    [None,  18.5,  17.8,  17.1],  # 13000
    [None,  17.5,  16.9,  None],  # 14000
    [None,  17.3,  16.7,  None],  # 15000
]

# ══════════════════════════════════════════════════════════════════════
# 65% RATED (169 HP)
# Fuel: 12.7 GPH best economy, 15.0 GPH best power
# RPM options: 2100, 2200, 2300, 2400
# ══════════════════════════════════════════════════════════════════════
RPMS_65 = [2100, 2200, 2300, 2400]

MAP_65 = [
    # 2100   2200   2300   2400     altitude
    [25.3,  24.1,  23.2,  22.2],  # SL
    [25.1,  23.9,  22.9,  22.0],  # 1000
    [24.8,  23.6,  22.7,  21.8],  # 2000
    [24.5,  23.4,  22.5,  21.6],  # 3000
    [24.2,  23.1,  22.2,  21.4],  # 4000
    [24.0,  22.9,  22.0,  21.1],  # 5000
    [23.7,  22.6,  21.7,  20.9],  # 6000
    [23.5,  22.4,  21.5,  20.7],  # 7000
    [None,  22.1,  21.2,  20.5],  # 8000
    [None,  21.9,  21.0,  20.3],  # 9000
    [None,  None,  20.7,  20.0],  # 10000
    [None,  None,  19.8,  None],  # 11000
    [None,  None,  None,  None],  # 12000
    [None,  None,  None,  None],  # 13000
    [None,  None,  None,  None],  # 14000
    [None,  None,  None,  None],  # 15000
]

# ══════════════════════════════════════════════════════════════════════
# 75% RATED (195 HP)
# Fuel: 14.1 GPH best economy, 16.5 GPH best power
# RPM options: 2200, 2300, 2400, 2500
# ══════════════════════════════════════════════════════════════════════
RPMS_75 = [2200, 2300, 2400, 2500]

MAP_75 = [
    # 2200   2300   2400   2500     altitude
    [26.9,  25.8,  24.8,  24.0],  # SL
    [26.6,  25.5,  24.5,  23.7],  # 1000
    [26.3,  25.3,  24.3,  23.5],  # 2000
    [26.0,  25.0,  24.0,  23.2],  # 3000
    [25.7,  24.7,  23.8,  22.9],  # 4000
    [25.4,  24.4,  23.5,  22.7],  # 5000
    [None,  24.1,  23.3,  22.4],  # 6000
    [None,  23.0,  22.2,  None],  # 7000  -- PDF shows only 2300/2400 at 7000
    [None,  None,  21.9,  None],  # 8000
    [None,  None,  None,  None],  # 9000
    [None,  None,  None,  None],  # 10000
    [None,  None,  None,  None],  # 11000
    [None,  None,  None,  None],  # 12000
    [None,  None,  None,  None],  # 13000
    [None,  None,  None,  None],  # 14000
    [None,  None,  None,  None],  # 15000
]

# ── Fuel flow data ──
FUEL_FLOW = {
    # percent_power: (best_economy_gph, best_power_gph)
    55: (11.4, 13.5),
    65: (12.7, 15.0),
    75: (14.1, 16.5),
}

# Map percent power to its table data
_POWER_TABLES = {
    55: (RPMS_55, MAP_55),
    65: (RPMS_65, MAP_65),
    75: (RPMS_75, MAP_75),
}


def get_map_required(pressure_alt_ft: float, rpm: int, percent_power: int,
                     oat_f: float = None) -> float | None:
    """Look up required manifold pressure.

    Args:
        pressure_alt_ft: Pressure altitude in feet
        rpm: Engine RPM (2100-2500 depending on power setting)
        percent_power: 55, 65, or 75
        oat_f: Actual OAT in degrees F (optional, for temperature correction).
               If None, assumes standard temperature.

    Returns:
        Required MAP in inches Hg, or None if that combination is
        beyond the engine's full-throttle capability at altitude.
    """
    if percent_power not in _POWER_TABLES:
        raise ValueError(f"percent_power must be 55, 65, or 75, got {percent_power}")

    rpms, table = _POWER_TABLES[percent_power]

    if rpm < rpms[0] or rpm > rpms[-1]:
        raise ValueError(f"RPM {rpm} out of range {rpms[0]}-{rpms[-1]} for {percent_power}%")

    result = interp_2d_with_none(
        pressure_alt_ft, float(rpm),
        [float(a) for a in ALTITUDES],
        [float(r) for r in rpms],
        table
    )

    if result is None:
        return None

    # Temperature correction: +0.17 in Hg per 10F above standard
    if oat_f is not None:
        std_temp = standard_temp_f(pressure_alt_ft)
        temp_delta_f = oat_f - std_temp
        result += 0.017 * temp_delta_f  # 0.17 per 10F = 0.017 per 1F

    return round(result, 1)


def get_fuel_flow(percent_power: int, mixture: str = "best_economy") -> float:
    """Get fuel flow in GPH for a power setting and mixture mode.

    Args:
        percent_power: 55, 65, or 75
        mixture: "best_economy" or "best_power"

    Returns:
        Fuel flow in gallons per hour.
    """
    if percent_power not in FUEL_FLOW:
        # Interpolate between known values
        powers = sorted(FUEL_FLOW.keys())
        idx = 0 if mixture == "best_economy" else 1
        flows = [FUEL_FLOW[p][idx] for p in powers]
        from ..utils.interpolation import interp_1d
        return round(interp_1d(float(percent_power),
                               [float(p) for p in powers],
                               flows), 1)

    idx = 0 if mixture == "best_economy" else 1
    return FUEL_FLOW[percent_power][idx]


def get_fuel_flow_interpolated(percent_power: float,
                               mixture: str = "best_economy") -> float:
    """Get fuel flow with interpolation for any power % between 55-75.

    Args:
        percent_power: Any value from 55 to 75
        mixture: "best_economy" or "best_power"

    Returns:
        Fuel flow in gallons per hour.
    """
    powers = sorted(FUEL_FLOW.keys())
    idx = 0 if mixture == "best_economy" else 1
    flows = [FUEL_FLOW[p][idx] for p in powers]
    return round(interp_1d(float(percent_power),
                           [float(p) for p in powers],
                           flows), 1)

"""Figure 5-03: Part Throttle Fuel Consumption

Lycoming IO-540-D series, Bendix RSA-5AD1 fuel injector.
Standard sea level conditions, compression ratio 8.5:1, min fuel grade 91/96.
Source: POH Section 5, page 5-7.
Digitized via WebPlotDigitizer (2026-03-29) from N9082P-Performance.pdf page 8.

X-axis: Actual Brake Horsepower (BHP).
Y-axis: Fuel Consumption (US gal/hr).

Each RPM/mixture combination is a straight line (2 endpoints).
To obtain fuel consumption at altitude, refer to Altitude Performance
Curve (Figure 5-04) to determine actual BHP available.

Note: POH fuel flow values (55%=11.4, 65%=12.7, 75%=14.1 best economy)
are at 2400 RPM. Cross-check against digitized 2400 RPM line: matches
within 0.1 GPH.
"""

from ..utils.interpolation import interp_1d

RATED_HP = 260.0

# ── Percent power to BHP mapping (from chart tick marks) ──
PERCENT_POWER = [45, 55, 65, 75, 85]
PERCENT_BHP = [116.1, 142.7, 169.2, 194.9, 220.6]

# ══════════════════════════════════════════════════════════════════════
# Digitized fuel flow lines: each is (BHP_low, GPH_low, BHP_high, GPH_high)
# Lines are straight -- interpolate linearly between endpoints.
# ══════════════════════════════════════════════════════════════════════

# Best Economy Mixture (peak EGT)
_ECON_LINES = {
    # RPM: (bhp_low, gph_low, bhp_high, gph_high)
    1800: (116.9, 8.68, 142.7, 10.01),
    2000: (116.9, 9.12, 169.2, 11.81),
    2200: (116.9, 9.56, 194.9, 13.66),
    2400: (116.9, 10.17, 194.9, 14.10),
    2600: (116.1, 10.49, 194.9, 14.50),
    2700: (116.9, 10.85, 194.9, 14.86),
}

# Best Power Mixture (100F rich of peak EGT)
_POWER_LINES = {
    # RPM: (bhp_low, gph_low, bhp_high, gph_high)
    2200: (116.9, 11.25, 214.9, 17.19),
    2400: (116.9, 11.69, 236.6, 19.15),
    2600: (116.1, 12.17, 256.7, 20.88),
    2700: (116.1, 12.61, 259.1, 21.52),
}

# RPM options available per mixture
RPMS_ECON = sorted(_ECON_LINES.keys())
RPMS_POWER = sorted(_POWER_LINES.keys())


def _interp_line(bhp: float, line: tuple) -> float:
    """Interpolate along a straight fuel flow line."""
    bhp_lo, gph_lo, bhp_hi, gph_hi = line
    if bhp_hi == bhp_lo:
        return gph_lo
    t = (bhp - bhp_lo) / (bhp_hi - bhp_lo)
    t = max(0.0, min(1.0, t))
    return gph_lo + t * (gph_hi - gph_lo)


def bhp_from_percent(percent_power: float) -> float:
    """Convert percent rated power to actual BHP."""
    return interp_1d(percent_power,
                     [float(p) for p in PERCENT_POWER],
                     [float(b) for b in PERCENT_BHP])


def percent_from_bhp(bhp: float) -> float:
    """Convert actual BHP to percent rated power."""
    return interp_1d(bhp,
                     [float(b) for b in PERCENT_BHP],
                     [float(p) for p in PERCENT_POWER])


def fuel_flow_gph(bhp: float, rpm: int = 2400,
                  mixture: str = "best_economy") -> float:
    """Look up fuel flow for a given BHP, RPM, and mixture setting.

    Args:
        bhp: Actual brake horsepower
        rpm: Engine RPM (1800-2700 for economy, 2200-2700 for power)
        mixture: "best_economy" (peak EGT) or "best_power" (100F ROP)

    Returns:
        Fuel flow in gallons per hour.
    """
    lines = _ECON_LINES if mixture == "best_economy" else _POWER_LINES
    available_rpms = sorted(lines.keys())

    if rpm in lines:
        return round(_interp_line(bhp, lines[rpm]), 1)

    # Interpolate between nearest RPM lines
    rpm_f = float(rpm)
    rpm_lo = max(r for r in available_rpms if r <= rpm_f) if any(r <= rpm_f for r in available_rpms) else available_rpms[0]
    rpm_hi = min(r for r in available_rpms if r >= rpm_f) if any(r >= rpm_f for r in available_rpms) else available_rpms[-1]

    if rpm_lo == rpm_hi:
        return round(_interp_line(bhp, lines[rpm_lo]), 1)

    gph_lo = _interp_line(bhp, lines[rpm_lo])
    gph_hi = _interp_line(bhp, lines[rpm_hi])
    t = (rpm_f - rpm_lo) / (rpm_hi - rpm_lo)
    return round(gph_lo + t * (gph_hi - gph_lo), 1)


def fuel_flow_from_percent(percent_power: float, rpm: int = 2400,
                           mixture: str = "best_economy") -> float:
    """Look up fuel flow for a given percent power setting.

    Args:
        percent_power: Percent of rated power (45-85)
        rpm: Engine RPM
        mixture: "best_economy" or "best_power"

    Returns:
        Fuel flow in gallons per hour.
    """
    bhp = bhp_from_percent(percent_power)
    return fuel_flow_gph(bhp, rpm, mixture)


def fuel_flow_climb() -> float:
    """Fuel flow during full-power climb (2700 RPM, best power, 260 BHP).

    From digitized chart: 21.6 GPH. POH flight planning example: 21.5 GPH.
    """
    return fuel_flow_gph(RATED_HP, 2700, "best_power")

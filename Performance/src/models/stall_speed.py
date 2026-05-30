"""Figure 5-05: Stall Speed vs Gross Weight

Power-off stall speeds at various weights and configurations.
Source: POH Section 5, page 5-9.

EXPERIMENTAL -- digitized approximation. Not validated.

Physics model: V_stall = V_ref * sqrt(W / W_ref)
This is derived from the lift equation: L = 0.5 * rho * V^2 * S * CL_max
At stall, L = W, so V_stall = sqrt(2W / (rho * S * CL_max))
For a given configuration, CL_max and S are constant, so V_stall ∝ sqrt(W).

Reference values from POH (at 3,100 lb gross weight):
    Clean (gear up, flaps up):     75 MPH CAS / 65 kt CAS
    15-deg flaps, gear down:       ~68 MPH CAS / ~59 kt CAS  (estimated from chart)
    Full flaps (32 deg), gear down: 67 MPH CAS / 58 kt CAS

Data points digitized from POH Figure 5-05 using WebPlotDigitizer (2026-03-29).
Chart source: N9082P-Performance.pdf (HQ scan), page 11.
X-axis: Gross Weight 1900-3100 lb
Y-axis: Stall Speed (dual scales: MPH CAS and knots CAS)
Digitized on the knots scale, converted to MPH (* 1/0.868976).
"""

import math
from ..utils.interpolation import interp_1d
from ..utils.units import mph_to_knots

# ── Data digitized from Figure 5-05 via WebPlotDigitizer ──
# Weight (lb) vs Stall Speed (MPH CAS)
# Source knot values: 50.3, 52.8, 55.2, 57.7, 60.2, 62.6, 65.1

# Flaps Up (clean configuration) -- "GEAR AND FLAPS RETRACTED"
WEIGHTS_CLEAN = [1903, 2102, 2302, 2502, 2699, 2900, 3099]
VSTALL_CLEAN_MPH = [57.9, 60.8, 63.5, 66.4, 69.3, 72.1, 74.9]

# Full Flaps (32 deg) + Gear Down -- "GEAR EXTENDED - FULL FLAPS"
# Source knot values: 45.6, 47.7, 49.8, 51.9, 54.0, 56.2, 58.3
WEIGHTS_FLAPS = [1902, 2102, 2300, 2500, 2700, 2899, 3099]
VSTALL_FLAPS_MPH = [52.5, 54.9, 57.3, 59.7, 62.2, 64.7, 67.1]

# Reference values for physics model
W_REF = 3100.0  # lb

# Reference stall speeds at gross weight (MPH CAS)
V_REF = {
    "clean": 75.0,
    "flaps_15_gear_down": 68.0,  # estimated
    "full_flaps_gear_down": 67.0,
}


def stall_speed_mph(weight_lb: float,
                    config: str = "clean") -> float:
    """Compute power-off stall speed in MPH CAS.

    Uses lookup table with linear interpolation for clean and full-flaps
    configurations, physics model for 15-deg flaps.

    Args:
        weight_lb: Aircraft weight in pounds (1900-3100)
        config: "clean", "flaps_15_gear_down", or "full_flaps_gear_down"

    Returns:
        Stall speed in MPH CAS.
    """
    if config == "clean":
        return interp_1d(weight_lb,
                         [float(w) for w in WEIGHTS_CLEAN],
                         VSTALL_CLEAN_MPH)
    elif config == "full_flaps_gear_down":
        return interp_1d(weight_lb,
                         [float(w) for w in WEIGHTS_FLAPS],
                         VSTALL_FLAPS_MPH)
    elif config == "flaps_15_gear_down":
        # No separate chart curve -- use physics model
        v_ref = V_REF["flaps_15_gear_down"]
        return v_ref * math.sqrt(weight_lb / W_REF)
    else:
        raise ValueError(f"Unknown config: {config}. "
                         "Use 'clean', 'flaps_15_gear_down', or 'full_flaps_gear_down'")


def stall_speed_knots(weight_lb: float,
                      config: str = "clean") -> float:
    """Compute power-off stall speed in knots CAS.

    Args:
        weight_lb: Aircraft weight in pounds (1900-3100)
        config: "clean", "flaps_15_gear_down", or "full_flaps_gear_down"

    Returns:
        Stall speed in knots CAS.
    """
    return round(mph_to_knots(stall_speed_mph(weight_lb, config)), 1)


def approach_speed_knots(weight_lb: float,
                         config: str = "full_flaps_gear_down",
                         factor: float = 1.3) -> float:
    """Compute approach speed (factor x Vso) in knots.

    POH specifies approach at 1.3 x Vso for landing charts.

    Args:
        weight_lb: Aircraft weight in pounds
        config: Landing configuration
        factor: Multiplier over stall speed (default 1.3 per POH)

    Returns:
        Approach speed in knots CAS.
    """
    vs = stall_speed_knots(weight_lb, config)
    return round(vs * factor, 0)

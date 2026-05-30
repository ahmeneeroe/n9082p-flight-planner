"""Standard atmosphere and density altitude calculations.

Based on ICAO Standard Atmosphere (ISA).
Reference: POH Figure 5-01 Altitude Conversion Chart.
"""

import math

# ISA constants
T0_R = 518.67       # Sea level standard temp (Rankine) = 59F
T0_F = 59.0         # Sea level standard temp (F)
T0_C = 15.0         # Sea level standard temp (C)
P0_INHG = 29.92     # Sea level standard pressure (in Hg)
LAPSE_F_PER_FT = 0.003566  # Standard lapse rate (F per foot)
LAPSE_C_PER_FT = 0.001981  # Standard lapse rate (C per foot)
RHO0 = 0.002377     # Sea level standard density (slugs/ft^3)


def standard_temp_f(pressure_alt_ft: float) -> float:
    """Standard temperature (F) at a given pressure altitude."""
    return T0_F - LAPSE_F_PER_FT * pressure_alt_ft


def standard_temp_c(pressure_alt_ft: float) -> float:
    """Standard temperature (C) at a given pressure altitude."""
    return T0_C - LAPSE_C_PER_FT * pressure_alt_ft


def pressure_ratio(pressure_alt_ft: float) -> float:
    """Pressure ratio (delta) at pressure altitude, troposphere only."""
    return (1 - 6.8756e-6 * pressure_alt_ft) ** 5.2559


def density_altitude(pressure_alt_ft: float, oat_f: float) -> float:
    """Compute density altitude from pressure altitude and OAT.

    Uses the NWS formula:
    DA = 145442.16 * (1 - (17.326 * P_station / T_rankine) ^ 0.235)

    More accurate than the Koch chart approximation, especially at
    large temperature deviations from standard.
    """
    oat_r = oat_f + 459.67
    p_station = P0_INHG * pressure_ratio(pressure_alt_ft)
    return 145442.16 * (1.0 - (17.326 * p_station / oat_r) ** 0.235)


def density_ratio(pressure_alt_ft: float, oat_f: float) -> float:
    """Density ratio (sigma = rho/rho0) at given conditions."""
    oat_r = oat_f + 459.67
    std_temp_r = standard_temp_f(pressure_alt_ft) + 459.67
    delta = pressure_ratio(pressure_alt_ft)
    theta = oat_r / T0_R
    return delta / theta


def density_altitude_from_density_ratio(sigma: float) -> float:
    """Approximate density altitude from density ratio.

    Inverts the relationship: at standard conditions,
    sigma decreases with altitude roughly as:
    DA ≈ (1 - sigma^0.235) / 6.8756e-6
    This is an approximation valid in the troposphere.
    """
    # Use iterative approach for accuracy
    # Start with linear approximation
    da = (1.0 - sigma) * 145442.0  # rough linear approx
    # Refine with a few Newton iterations
    for _ in range(5):
        std_t_f = standard_temp_f(da)
        std_t_r = std_t_f + 459.67
        delta = pressure_ratio(da)
        sigma_calc = delta * T0_R / std_t_r
        dsigma = sigma_calc - sigma
        da += dsigma * 30000.0  # approximate sensitivity
    return da

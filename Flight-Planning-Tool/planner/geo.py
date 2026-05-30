"""Geometry + atmosphere helpers: great-circle distance/course, wind components,
pressure altitude. Pure standard library.
"""
import math

_NM_PER_RAD = 3440.065  # earth radius in nautical miles


def haversine_nm(lat1, lon1, lat2, lon2):
    """Great-circle distance in nautical miles."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * _NM_PER_RAD * math.asin(min(1.0, math.sqrt(a)))


def initial_bearing(lat1, lon1, lat2, lon2):
    """Initial true course (degrees) from point 1 to point 2."""
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dl = math.radians(lon2 - lon1)
    x = math.sin(dl) * math.cos(p2)
    y = math.cos(p1) * math.sin(p2) - math.sin(p1) * math.cos(p2) * math.cos(dl)
    return (math.degrees(math.atan2(x, y)) + 360) % 360


def wind_components(wind_dir, wind_kt, runway_hdg):
    """(headwind_kt, crosswind_kt) for a runway heading.

    Wind direction is where the wind comes FROM; runway heading is the direction
    of travel. headwind < 0 means a tailwind. Crosswind is returned as magnitude.
    Per the validated prototype, both wind (true, from METAR) and runway heading
    (from the runway number) are treated on the same datum -- variation is ignored.
    """
    if wind_dir is None or wind_kt is None or runway_hdg is None:
        return 0.0, 0.0
    theta = math.radians(((wind_dir - runway_hdg + 540) % 360) - 180)
    return wind_kt * math.cos(theta), abs(wind_kt * math.sin(theta))


def pressure_altitude(field_elev_ft, altimeter_inhg):
    """Pressure altitude from field elevation and altimeter setting (in Hg)."""
    if altimeter_inhg is None:
        return float(field_elev_ft)
    return field_elev_ft + (29.92 - altimeter_inhg) * 1000.0


def density_altitude(pressure_alt_ft, oat_f):
    """Density altitude (ft) from pressure altitude and OAT (deg F).

    NWS formula -- identical to the performance calculator's atmosphere util,
    duplicated here so the planner has no dependency on the calculator's module path.
    """
    oat_r = oat_f + 459.67
    p_ratio = (1 - 6.8756e-6 * pressure_alt_ft) ** 5.2559
    p_station = 29.92 * p_ratio
    return 145442.16 * (1.0 - (17.326 * p_station / oat_r) ** 0.235)

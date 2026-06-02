"""Build the N9082P preflight safety sheet (structured data).

Pipeline: resolve airports (FAA AIS) -> fetch weather (NWS METAR) -> compute
pressure/density altitude + wind components -> estimate landing weight ->
run the POH performance calculator per runway -> assemble a sheet dict.

render.py turns the sheet dict into the A5 HTML. Nothing here is FAA-approved;
all performance figures are digitized POH approximations with a 5% bias.
"""
import datetime
import time

from . import data, geo, safety, weather
from .perf import N9082P

LB_PER_GAL = 6.0
MAX_GROSS = 3100
MAX_LANDING = 2945
DEFAULT_FUEL_GAL = 86
BEST_GLIDE_GROSS_KT = 91  # POH Sec 3 p3-2: optimum (max-distance) glide at 3100 lb gross

# FAA surface category (from the data bundle) -> calculator surface key.
_SURFACE_TO_CALC = {
    "paved_dry": "paved_dry",
    "grass": "dry_grass_short",
    "gravel": "soft_ground",
    "water": "paved_dry",
}


def _std_temp_f(alt_ft):
    return 59.0 - 0.003566 * alt_ft


def _best_glide_kt(weight_lb):
    """Best-glide (max-distance) speed in KIAS at a given weight -- DERIVED ESTIMATE, not POH.

    POH Sec 3 (p3-2 / p3-5) gives 91 kt only at 3100 lb gross and notes *qualitatively* that
    best glide "decreases as gross weight decreases" (no rate). Best-L/D speed scales with
    sqrt(weight), so scale the POH gross value: 91 * sqrt(W / 3100). Clamped to <= the gross value.
    """
    w = min(weight_lb, MAX_GROSS)
    return round(BEST_GLIDE_GROSS_KT * (w / MAX_GROSS) ** 0.5)


class AirportNotFound(ValueError):
    pass


def _weather_or_default(apt):
    """Fetch METAR for an airport, or synthesize a standard-day fallback."""
    wx = None
    try:
        wx = weather.weather_for_airport(apt)
    except Exception:
        wx = None
    if wx and wx.get("temp_f") is not None and wx.get("altimeter_inhg") is not None:
        wx["available"] = True
        return wx
    return {
        "available": False, "station": None, "distance_nm": None,
        "temp_f": round(_std_temp_f(apt["elev_ft"])),
        "altimeter_inhg": 29.92, "wind_dir": None, "wind_kt": None,
        "wind_variable": False, "gust_kt": None, "obs_time": None,
        "raw": None,
    }


def _wind_label(wx):
    if not wx.get("available"):
        return "Std day (no METAR)"
    if wx.get("wind_variable") or (wx.get("wind_kt") or 0) == 0:
        return "Calm"
    g = wx.get("gust_kt")
    base = f"{wx['wind_dir']:03d}°/{wx['wind_kt']}kt"
    return base + (f" G{g}" if g else "")


def _wind_phrase(headwind_kt):
    h = round(headwind_kt)
    if h >= 1:
        return f"{h} kt headwind"
    if h <= -1:
        return f"{-h} kt TAILWIND"
    return "calm/crosswind"


def _favored_ends(apt, wx, limit=3):
    """For the longest `limit` runways, pick the wind-favored end of each."""
    wdir = wx.get("wind_dir")
    wkt = wx.get("wind_kt")
    ends = []
    for rw in apt["runways"][:limit]:
        cands = []
        if rw.get("le_hdg") is not None:
            hw, xw = geo.wind_components(wdir, wkt, rw["le_hdg"])
            cands.append((rw["le_ident"], rw["le_hdg"], hw, xw))
        if rw.get("he_hdg") is not None:
            hw, xw = geo.wind_components(wdir, wkt, rw["he_hdg"])
            cands.append((rw["he_ident"], rw["he_hdg"], hw, xw))
        if not cands:
            continue
        ident, hdg, hw, xw = max(cands, key=lambda c: c[2])  # most headwind
        ends.append({"runway": rw, "ident": ident, "hdg": hdg,
                     "headwind": hw, "crosswind": xw})
    return ends


def _row(label, required_ft, available_ft):
    required_ft = max(1, round(required_ft))
    ratio = available_ft / required_ft
    return {
        "label": label,
        "required": required_ft,
        "margin": round(available_ft) - required_ft,
        "ratio": round(ratio, 1),
        "badge": safety.runway_badge(ratio),
    }


def _runways_label(apt):
    return "  |  ".join(
        f"{rw['designator']}: {rw['length_ft']}" for rw in apt["runways"][:3])


def _airport_block(apt, wx, calc, weight_lb, phase):
    """phase = 'takeoff' or 'landing'."""
    pa = round(geo.pressure_altitude(apt["elev_ft"], wx["altimeter_inhg"]))
    oat = wx["temp_f"]
    da = round(geo.density_altitude(pa, oat))

    tables = []
    for fe in _favored_ends(apt, wx):
        rw = fe["runway"]
        length = rw["length_ft"]
        hw = fe["headwind"]
        surf = _SURFACE_TO_CALC.get(rw["surface"], "paved_dry")
        if phase == "takeoff":
            t = calc.takeoff(pressure_alt_ft=pa, oat_f=oat, weight_lb=weight_lb,
                             headwind_kt=hw, surface=surf)
            sf_g, sf_50 = t["ground_run_ft"], t["over_50ft_obstacle_ft"]
            rows = [
                _row("SF ground run", sf_g, length),
                _row("SF over 50 ft", sf_50, length),
                _row("Std ground run", t["ground_run_standard_ft"], length),
                _row("Std over 50 ft", sf_50 * 2, length),
            ]
            verb = "Takeoff"
        else:
            t = calc.landing(pressure_alt_ft=pa, oat_f=oat,
                             weight_lb=min(weight_lb, MAX_LANDING),
                             headwind_kt=hw, surface=surf)
            sf_g, sf_50 = t["ground_roll_ft"], t["over_50ft_obstacle_ft"]
            rows = [
                _row("SF ground roll", sf_g, length),
                _row("SF over 50 ft", sf_50, length),
                _row("Std ground roll", t["ground_roll_standard_ft"], length),
                _row("Std over 50 ft", sf_50 * 2, length),
            ]
            verb = "Landing"
        tables.append({
            "title": f"{verb} — Rwy {fe['ident']} ({length} ft), {_wind_phrase(hw)}",
            "runway": rw["designator"], "ident": fe["ident"],
            "length_ft": length, "crosswind": round(fe["crosswind"]),
            "crosswind_badge": safety.crosswind_badge(fe["crosswind"]),
            "rows": rows,
            "limiting_ratio": round(length / max(1, sf_50 * 2), 1),  # std over-50
        })

    stall = calc.stall(weight_lb if phase == "takeoff" else min(weight_lb, MAX_LANDING))
    speeds = {
        "vs_clean": round(stall["clean_kt"]),
        "vs_15": round(stall["flaps_15_gear_down_kt"]),
        "vs_full": round(stall["full_flaps_gear_down_kt"]),
    }
    if phase == "takeoff":
        cl = calc.climb(pa, oat, weight_lb=weight_lb)
        speeds.update(vx=cl["vx_kt"], vy=cl["vy_kt"], roc=cl["rate_of_climb_fpm"])
    else:
        speeds["vapp"] = round(stall["approach_speed_kt"])
        cl = calc.climb(pa, oat, weight_lb=weight_lb)  # climb capability at field DA + landing wt
        speeds["roc"] = cl["rate_of_climb_fpm"]
        speeds["vy"] = cl["vy_kt"]

    remark_bits = []
    if apt["runways"]:
        r0 = apt["runways"][0]
        remark_bits.append(f"Rwy surface: {r0.get('surface_raw') or r0['surface']}"
                           + (", lighted" if r0.get("lighted") else ""))
    if wx.get("available") and wx.get("distance_nm"):
        remark_bits.append(f"WX from {wx['station']} ({wx['distance_nm']} nm)")
    elif not wx.get("available"):
        remark_bits.append("No METAR — standard day assumed; enter conditions manually")

    return {
        "id": apt["ident"], "name": apt["name"], "elev": apt["elev_ft"],
        "private": apt.get("private"), "runways_label": _runways_label(apt),
        "temp_f": oat, "pa": pa, "da": da, "wind_label": _wind_label(wx),
        "tables": tables, "speeds": speeds, "phase": phase,
        "remarks": remark_bits,
    }


def _estimate_burn(calc, dep, dep_block_pa, dep_oat, dest, tow,
                   cruise_alt, power, rpm, mixture, fuel_gal):
    """Rough total fuel burn (gal) dep->dest for a landing-weight estimate."""
    dist = 0.0
    if dep.get("lat") is not None and dest.get("lat") is not None:
        dist = geo.haversine_nm(dep["lat"], dep["lon"], dest["lat"], dest["lon"])
    try:
        climb_fuel = calc.climb(dep_block_pa, dep_oat, target_alt_ft=cruise_alt,
                                weight_lb=tow).get("fuel_to_climb_gal", 2.0)
    except Exception:
        climb_fuel = 2.0
    try:
        cr = calc.cruise(cruise_alt, _std_temp_f(cruise_alt), percent_power=power,
                         rpm=rpm, mixture=mixture, fuel_gal=fuel_gal)
        tas = cr.get("tas_kt") or 145.0
        gph = cr.get("fuel_flow_gph") or 13.0
    except Exception:
        tas, gph = 145.0, 13.0
    enroute = (dist / tas) * gph if tas else 0.0
    burn = 1.0 + climb_fuel + enroute  # taxi + climb + cruise
    return burn, dist


def build_sheet(dep_id, dest_id, takeoff_weight_lb, fuel_gal=DEFAULT_FUEL_GAL,
                cruise_alt_ft=7500, power=65, rpm=2400, mixture="best_economy",
                landing_weight_lb=None, now=None):
    dep = data.lookup(dep_id)
    if not dep:
        raise AirportNotFound(f"Departure airport '{dep_id}' not found in FAA data.")
    dest = data.lookup(dest_id)
    if not dest:
        raise AirportNotFound(f"Destination airport '{dest_id}' not found in FAA data.")

    calc = N9082P()
    dep_wx = _weather_or_default(dep)
    dest_wx = _weather_or_default(dest)

    dep_pa = round(geo.pressure_altitude(dep["elev_ft"], dep_wx["altimeter_inhg"]))
    burn, dist_nm = _estimate_burn(calc, dep, dep_pa, dep_wx["temp_f"], dest,
                                   takeoff_weight_lb, cruise_alt_ft, power, rpm,
                                   mixture, fuel_gal)
    if landing_weight_lb is None:
        landing_weight_lb = max(1900.0, takeoff_weight_lb - burn * LB_PER_GAL)
    glide_weight = (takeoff_weight_lb + landing_weight_lb) / 2.0  # mid-flight weight
    best_glide_kt = _best_glide_kt(glide_weight)

    dep_block = _airport_block(dep, dep_wx, calc, takeoff_weight_lb, "takeoff")
    dest_block = _airport_block(dest, dest_wx, calc, landing_weight_lb, "landing")

    summary = [
        {"label": "TO Wt", "val": f"{round(takeoff_weight_lb)}/{MAX_GROSS}",
         "badge": safety.weight_badge(takeoff_weight_lb, MAX_GROSS)},
        {"label": "LDG Wt", "val": f"{round(landing_weight_lb)}/{MAX_LANDING}",
         "badge": safety.weight_badge(landing_weight_lb, MAX_LANDING)},
        {"label": f"DA {dep['ident']}", "val": str(dep_block["da"]),
         "badge": safety.density_alt_badge(dep_block["da"])},
        {"label": f"DA {dest['ident']}", "val": str(dest_block["da"]),
         "badge": safety.density_alt_badge(dest_block["da"])},
    ]
    for blk in (dep_block, dest_block):
        for tbl in blk["tables"]:
            summary.append({
                "label": f"{blk['id']} {tbl['runway']}",
                "val": f"{tbl['limiting_ratio']}×",
                "badge": safety.runway_badge(tbl["limiting_ratio"]),
            })

    now = now or datetime.datetime.now(datetime.timezone.utc)
    dep_age = _metar_age_min(dep_wx, now)
    dest_age = _metar_age_min(dest_wx, now)

    return {
        "tail": "N9082P",
        "route": f"{dep['ident']} → {dest['ident']}",
        "generated": now.strftime("%Y-%m-%d %H:%MZ"),
        "to_weight": round(takeoff_weight_lb),
        "ldg_weight": round(landing_weight_lb),
        "best_glide_kt": best_glide_kt,
        "glide_weight": round(glide_weight),
        "fuel_gal": round(fuel_gal),
        "burn_gal": round(burn),
        "dist_nm": round(dist_nm),
        "power": f"{round(power)}%", "rpm": rpm,
        "mixture": "best economy" if mixture == "best_economy" else "best power",
        "max_gross": MAX_GROSS, "max_landing": MAX_LANDING,
        "dep": dep_block, "dest": dest_block, "summary": summary,
        "metar_age": {"dep": dep_age, "dest": dest_age},
        "data_built": data.meta().get("built"),
        "notes": ("EXPERIMENTAL — digitized POH Sec 5 charts, 5% conservative bias, "
                  "NOT flight-tested. Std = 2× short-field. Verify against the POH. "
                  "Wind components use runway number vs METAR wind. "
                  "Best glide 91 kt @ gross = POH Sec 3; mid-flight value is a derived sqrt-weight "
                  "estimate. Dest climb = ROC at landing weight + field METAR."),
    }


def _metar_age_min(wx, now):
    if not wx.get("obs_time"):
        return None
    return round((now.timestamp() - wx["obs_time"]) / 60)

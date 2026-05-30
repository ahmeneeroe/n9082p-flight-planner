"""METAR fetch + parse from aviationweather.gov (NOAA/NWS Aviation Weather Center).

This is the U.S. government's authoritative aviation weather source -- the one the
FAA directs pilots to. Standard library only (urllib), so it runs in Lambda.
"""
import json
import urllib.parse
import urllib.request

from . import geo

_API = "https://aviationweather.gov/api/data/metar"
_UA = "n9082p-flight-planner/1.0"


def _get(params):
    url = _API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": _UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read().decode())


def _parse(ob):
    temp_c = ob.get("temp")
    altim_hpa = ob.get("altim")
    wdir = ob.get("wdir")
    return {
        "station": ob.get("icaoId"),
        "name": ob.get("name"),
        "temp_c": temp_c,
        "temp_f": round(temp_c * 9 / 5 + 32) if temp_c is not None else None,
        "altimeter_inhg": round(altim_hpa * 0.02953, 2) if altim_hpa is not None else None,
        "wind_dir": wdir if isinstance(wdir, (int, float)) else None,  # 'VRB' -> None
        "wind_variable": wdir == "VRB",
        "wind_kt": ob.get("wspd"),
        "gust_kt": ob.get("wgst"),
        "raw": ob.get("rawOb"),
        "obs_time": ob.get("obsTime"),
        "lat": ob.get("lat"),
        "lon": ob.get("lon"),
    }


def metar_for_station(station):
    """METAR for a specific ICAO station id, or None."""
    data = _get({"ids": station, "format": "json"})
    return _parse(data[0]) if data else None


def nearest_metar(lat, lon, radius_deg=1.5):
    """Nearest reporting station to a lat/lon (bbox query), picked by distance."""
    bbox = f"{lat - radius_deg},{lon - radius_deg},{lat + radius_deg},{lon + radius_deg}"
    data = _get({"bbox": bbox, "format": "json"})
    if not data:
        return None
    best, best_d = None, float("inf")
    for ob in data:
        olat, olon = ob.get("lat"), ob.get("lon")
        if olat is None or olon is None or ob.get("temp") is None:
            continue
        d = geo.haversine_nm(lat, lon, olat, olon)
        if d < best_d:
            best, best_d = ob, d
    if best is None:
        return None
    out = _parse(best)
    out["distance_nm"] = round(best_d, 1)
    return out


def weather_for_airport(apt):
    """METAR for an airport: its own station if it reports, else the nearest station.

    Returns the parsed dict (with 'distance_nm' set when a nearby station was used),
    or None if nothing could be fetched.
    """
    if apt.get("icao"):
        m = metar_for_station(apt["icao"])
        if m and m.get("temp_c") is not None:
            m["distance_nm"] = 0.0
            return m
    if apt.get("lat") is not None and apt.get("lon") is not None:
        return nearest_metar(apt["lat"], apt["lon"])
    return None

"""FAA AIS airport data lookup (bundled data/airports_faa.json).

The bundle is built from FAA Aeronautical Information Services data by
tools/build_faa_airports.py and refreshed monthly (FAA 28-day cycle).
"""
import json
import os

_DATA_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "airports_faa.json")
_DATA = None  # cached across warm Lambda invocations


def _load():
    global _DATA
    if _DATA is None:
        with open(_DATA_PATH) as f:
            _DATA = json.load(f)
    return _DATA


def lookup(identifier):
    """Resolve an FAA LID or ICAO id (e.g. 'S95', 'KALW') to an airport record, or None."""
    if not identifier:
        return None
    d = _load()
    gid = d["index"].get(identifier.strip().upper())
    if not gid:
        return None
    apt = dict(d["airports"][gid])
    apt["id"] = gid
    return apt


def meta():
    return _load().get("_meta", {})

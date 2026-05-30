#!/usr/bin/env python3
"""Build data/airports_faa.json from FAA Aeronautical Information Services (AIS) data.

Source: FAA AIS open data -- the data shown on FAA aeronautical charts -- served from
ArcGIS FeatureServers owned by the FAA org 'AeronauticalInformationServices_FAA':
  Airports: .../US_Airport/FeatureServer/0
  Runways : .../Runways/FeatureServer/0

This is FAA-authoritative airport/runway data (the same source behind the Chart
Supplement / 5010 master record). It tracks the FAA 28-day charting cycle, so rerun
this monthly and redeploy.

Uses only the Python standard library (urllib) so it can also run as a refresh Lambda.

Usage:  python3 tools/build_faa_airports.py [out.json]
"""
import datetime, json, os, sys, urllib.parse, urllib.request

ORG = "https://services6.arcgis.com/ssFJjBXIUyZDrSYZ/arcgis/rest/services"
AIRPORTS = f"{ORG}/US_Airport/FeatureServer/0/query"
RUNWAYS = f"{ORG}/Runways/FeatureServer/0/query"
UA = "n9082p-flight-planner/1.0 (FAA AIS bulk fetch)"

# FAA COMP_CODE (surface composition) -> performance-calculator surface category.
SURFACE_MAP = {
    "ASPH": "paved_dry", "CONC": "paved_dry", "ASPH-CONC": "paved_dry",
    "PEM": "paved_dry", "ASPH-PFC": "paved_dry", "CONC-G": "paved_dry",
    "ASPH-G": "paved_dry", "ASPH-E": "paved_dry",
    "TURF": "grass", "TURF-G": "grass", "GRASS": "grass", "TURF-F": "grass",
    "GRVL": "gravel", "GRAVEL": "gravel", "GVL": "gravel", "DIRT": "gravel",
    "SAND": "gravel", "WATER": "water",
}


def fetch_all(url, out_fields, where="1=1", page=2000):
    """Page through an ArcGIS FeatureServer layer, returning all attribute rows."""
    rows, offset = [], 0
    while True:
        params = {
            "where": where, "outFields": out_fields, "returnGeometry": "false",
            "orderByFields": "OBJECTID", "resultOffset": offset,
            "resultRecordCount": page, "f": "json",
        }
        req = urllib.request.Request(url + "?" + urllib.parse.urlencode(params),
                                     headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode())
        if "error" in data:
            raise RuntimeError(f"ArcGIS error: {data['error']}")
        feats = data.get("features", [])
        rows.extend(f["attributes"] for f in feats)
        if not feats or (not data.get("exceededTransferLimit") and len(feats) < page):
            break
        offset += len(feats)
        print(f"  ... {len(rows)} records", flush=True)
    return rows


def dms_to_decimal(s):
    """FAA coordinate string -> decimal degrees. Never raises (returns None on failure).

    Handles '46-02-48.9810N' (DMS), '46-02N' (deg-min), '46.05N' (decimal+hemisphere),
    and bare signed decimals. W/S are negative.
    """
    if not s:
        return None
    s = s.strip()
    if not s:
        return None
    hemi = s[-1].upper()
    if hemi in "NSEW":
        sign = -1 if hemi in "SW" else 1
        try:
            nums = [float(p) for p in s[:-1].split("-") if p != ""]
        except ValueError:
            return None
        if not nums:
            return None
        deg = nums[0]
        minute = nums[1] if len(nums) > 1 else 0.0
        sec = nums[2] if len(nums) > 2 else 0.0
        return round(sign * (deg + minute / 60 + sec / 3600), 6)
    try:
        return round(float(s), 6)
    except ValueError:
        return None


def heading_from_end(end):
    """Runway designator end -> magnetic-ish heading. '05'->50, '28L'->280, '36'->360."""
    digits = ""
    for ch in (end or "").strip():
        if ch.isdigit():
            digits += ch
        else:
            break
    if not digits:
        return None
    n = int(digits) % 36
    return float((n if n else 36) * 10)


def norm_surface(code):
    c = (code or "").strip().upper()
    return SURFACE_MAP.get(c, "paved_dry"), (code or "").strip()


def main(out_path):
    print("Fetching FAA AIS runways ...", flush=True)
    rwy_rows = fetch_all(
        RUNWAYS, "AIRPORT_ID,DESIGNATOR,LENGTH,WIDTH,COMP_CODE,DIM_UOM,LIGHTACTV")
    by_airport = {}
    for a in rwy_rows:
        if (a.get("DIM_UOM") or "FT") != "FT":
            continue
        length = a.get("LENGTH") or 0
        if not length:
            continue
        ends = (a.get("DESIGNATOR") or "").split("/")
        le_hdg = heading_from_end(ends[0]) if ends else None
        he_hdg = heading_from_end(ends[1]) if len(ends) > 1 else None
        if le_hdg is None and he_hdg is None:
            continue  # helipad (H1) / water lane / unnumbered -- not a fixed-wing runway
        cat, raw = norm_surface(a.get("COMP_CODE"))
        by_airport.setdefault(a["AIRPORT_ID"], []).append({
            "designator": a.get("DESIGNATOR") or "",
            "le_ident": ends[0] if ends else "",
            "he_ident": ends[1] if len(ends) > 1 else "",
            "le_hdg": le_hdg,
            "he_hdg": he_hdg,
            "length_ft": int(round(length)),
            "width_ft": int(round(a.get("WIDTH") or 0)),
            "surface": cat, "surface_raw": raw,
            "lighted": bool(a.get("LIGHTACTV")),
        })

    print("Fetching FAA AIS airports ...", flush=True)
    apt_rows = fetch_all(
        AIRPORTS,
        "GLOBAL_ID,IDENT,ICAO_ID,NAME,ELEVATION,LATITUDE,LONGITUDE,TYPE_CODE,"
        "STATE,SERVCITY,PRIVATEUSE,IAPEXISTS,OPERSTATUS",
        where="OPERSTATUS='OPERATIONAL' AND TYPE_CODE='AD'")

    airports, index, skipped = {}, {}, 0
    for a in apt_rows:
        try:
            gid = a["GLOBAL_ID"]
            rwys = sorted(by_airport.get(gid, []), key=lambda r: -r["length_ft"])
            airports[gid] = {
                "ident": a.get("IDENT"), "icao": a.get("ICAO_ID"),
                "name": a.get("NAME"), "elev_ft": round(a.get("ELEVATION") or 0),
                "lat": dms_to_decimal(a.get("LATITUDE")),
                "lon": dms_to_decimal(a.get("LONGITUDE")),
                "city": a.get("SERVCITY"), "state": a.get("STATE"),
                "private": bool(a.get("PRIVATEUSE")), "iap": bool(a.get("IAPEXISTS")),
                "runways": rwys,
            }
            for key in (a.get("IDENT"), a.get("ICAO_ID")):
                if key and key.strip():
                    index[key.strip().upper()] = gid
        except Exception as e:  # don't let one malformed record kill the build
            skipped += 1
            print(f"  skip {a.get('IDENT')}: {e}", flush=True)

    out = {"_meta": {"source": "FAA AIS (AeronauticalInformationServices_FAA)",
                     "airports": len(airports), "index_keys": len(index),
                     "skipped": skipped,
                     "built": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%MZ"),
                     "note": "Rerun monthly (FAA 28-day cycle) and redeploy."},
           "index": index, "airports": airports}
    os.makedirs(os.path.dirname(os.path.abspath(out_path)), exist_ok=True)
    with open(out_path, "w") as f:
        json.dump(out, f, separators=(",", ":"))

    print(f"\nwrote {out_path}: {len(airports)} airports, {len(index)} keys, "
          f"{skipped} skipped, {os.path.getsize(out_path) // 1024} KB")
    for q in ["S95", "S33", "7S3", "ALW", "KALW", "BOI", "KBOI"]:
        gid = index.get(q.upper())
        a = airports.get(gid) if gid else None
        if a:
            rws = ", ".join(f"{r['designator']} {r['length_ft']}ft {r['surface']}"
                            for r in a["runways"])
            print(f"  {q:5s} -> {a['name'][:24]:24s} elev={a['elev_ft']:>5}  [{rws}]")
        else:
            print(f"  {q:5s} -> NOT FOUND")


if __name__ == "__main__":
    default = os.path.join(os.path.dirname(__file__), "..", "data", "airports_faa.json")
    main(sys.argv[1] if len(sys.argv) > 1 else default)

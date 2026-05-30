"""FAA AIS airport data lookup.

Loads the airport bundle from S3 when DATA_BUCKET is set (kept current by the monthly
refresher Lambda), otherwise from the bundled data/airports_faa.json. The S3 object is
cached in /tmp + module memory per container; ANY S3 failure falls back to the bundled
baseline, so the app always works even if S3 is unavailable or empty.
"""
import json
import os

_BUNDLED = os.path.join(os.path.dirname(__file__), "..", "data", "airports_faa.json")
_BUCKET = os.environ.get("DATA_BUCKET")
_KEY = os.environ.get("DATA_KEY", "airports_faa.json")
_CACHE = "/tmp/airports_faa.json"
_DATA = None  # cached across warm invocations


def _load_from_s3():
    import boto3  # provided by the Lambda runtime; only imported when DATA_BUCKET is set
    if not os.path.exists(_CACHE) or os.path.getsize(_CACHE) == 0:
        boto3.client("s3").download_file(_BUCKET, _KEY, _CACHE)
    with open(_CACHE) as f:
        return json.load(f)


def _load():
    global _DATA
    if _DATA is not None:
        return _DATA
    if _BUCKET:
        try:
            _DATA = _load_from_s3()
            print(f"[data] source=s3 ({_BUCKET}/{_KEY})")
            return _DATA
        except Exception as e:
            print(f"[data] s3 load failed ({e!r}); falling back to bundled")
            try:
                if os.path.exists(_CACHE):
                    os.remove(_CACHE)  # drop a bad cache so the next cold start retries S3
            except OSError:
                pass
            _DATA = None  # fall through to the bundled baseline
    with open(_BUNDLED) as f:
        _DATA = json.load(f)
    print("[data] source=bundled")
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

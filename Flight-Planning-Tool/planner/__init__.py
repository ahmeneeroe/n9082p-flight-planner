"""N9082P flight planning package.

Combines FAA AIS airport data + NOAA/NWS weather (METAR) + the POH-derived
performance calculator into a preflight A5 safety sheet.

EXPERIMENTAL: performance figures come from digitized POH Section 5 charts
(5% conservative bias) and are NOT validated against flight test data.
Always verify against the POH.
"""

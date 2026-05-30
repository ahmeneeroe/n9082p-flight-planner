"""Safety thresholds and OK/CAU/WARN badges for the A5 sheet.

Thresholds per design.md. Runway ratio = runway available / distance required.
"""

CROSSWIND_DEMONSTRATED_KT = 17  # PA-24-260 demonstrated crosswind


def runway_badge(ratio):
    if ratio >= 2.0:
        return "ok"
    if ratio >= 1.5:
        return "cau"
    return "warn"


def crosswind_badge(crosswind_kt):
    if crosswind_kt < 12:
        return "ok"
    if crosswind_kt <= CROSSWIND_DEMONSTRATED_KT:
        return "cau"
    return "warn"


def density_alt_badge(da_ft):
    if da_ft < 5000:
        return "ok"
    if da_ft <= 8000:
        return "cau"
    return "warn"


def weight_badge(weight_lb, limit_lb):
    return "warn" if weight_lb > limit_lb else "ok"

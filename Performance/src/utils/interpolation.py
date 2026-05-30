"""Interpolation utilities for performance chart lookup tables.

Provides 1-D linear, 2-D bilinear, and 3-D trilinear interpolation
over regular and irregular grids of digitized chart data.
"""

import bisect
from typing import List, Optional


def lerp(x: float, x0: float, x1: float, y0: float, y1: float) -> float:
    """Linear interpolation between two points. Clamps to endpoints."""
    if x1 == x0:
        return y0
    t = (x - x0) / (x1 - x0)
    t = max(0.0, min(1.0, t))  # clamp -- no extrapolation
    return y0 + t * (y1 - y0)


def interp_1d(x: float, xs: List[float], ys: List[float]) -> float:
    """1-D piecewise linear interpolation.

    Args:
        x: input value
        xs: sorted breakpoints (ascending)
        ys: corresponding output values

    Returns:
        Interpolated value, clamped to table bounds.
    """
    if x <= xs[0]:
        return ys[0]
    if x >= xs[-1]:
        return ys[-1]
    i = bisect.bisect_right(xs, x) - 1
    return lerp(x, xs[i], xs[i + 1], ys[i], ys[i + 1])


def interp_2d(x: float, y: float,
              xs: List[float], ys: List[float],
              table: List[List[float]]) -> float:
    """2-D bilinear interpolation over a regular grid.

    Args:
        x, y: input values
        xs: row breakpoints (ascending), length M
        ys: column breakpoints (ascending), length N
        table: M x N grid of values, table[i][j] = f(xs[i], ys[j])

    Returns:
        Interpolated value, clamped to table bounds.
    """
    # Clamp x
    x = max(xs[0], min(xs[-1], x))
    y = max(ys[0], min(ys[-1], y))

    # Find bracketing indices
    ix = bisect.bisect_right(xs, x) - 1
    ix = min(ix, len(xs) - 2)
    iy = bisect.bisect_right(ys, y) - 1
    iy = min(iy, len(ys) - 2)

    # Bilinear interpolation
    tx = (x - xs[ix]) / (xs[ix + 1] - xs[ix]) if xs[ix + 1] != xs[ix] else 0.0
    ty = (y - ys[iy]) / (ys[iy + 1] - ys[iy]) if ys[iy + 1] != ys[iy] else 0.0

    v00 = table[ix][iy]
    v01 = table[ix][iy + 1]
    v10 = table[ix + 1][iy]
    v11 = table[ix + 1][iy + 1]

    return (v00 * (1 - tx) * (1 - ty) +
            v10 * tx * (1 - ty) +
            v01 * (1 - tx) * ty +
            v11 * tx * ty)


def interp_2d_with_none(x: float, y: float,
                        xs: List[float], ys: List[float],
                        table: List[List[Optional[float]]]) -> Optional[float]:
    """2-D bilinear interpolation that handles None values (off-chart regions).

    Returns None only if a corner with non-zero weight is None.
    When the query point is exactly on a grid line, corners with zero
    weight are ignored (allows lookups at the boundary of valid regions).
    """
    x = max(xs[0], min(xs[-1], x))
    y = max(ys[0], min(ys[-1], y))

    ix = bisect.bisect_right(xs, x) - 1
    ix = min(ix, len(xs) - 2)
    iy = bisect.bisect_right(ys, y) - 1
    iy = min(iy, len(ys) - 2)

    tx = (x - xs[ix]) / (xs[ix + 1] - xs[ix]) if xs[ix + 1] != xs[ix] else 0.0
    ty = (y - ys[iy]) / (ys[iy + 1] - ys[iy]) if ys[iy + 1] != ys[iy] else 0.0

    v00 = table[ix][iy]
    v01 = table[ix][iy + 1]
    v10 = table[ix + 1][iy]
    v11 = table[ix + 1][iy + 1]

    # Compute weights
    w00 = (1 - tx) * (1 - ty)
    w10 = tx * (1 - ty)
    w01 = (1 - tx) * ty
    w11 = tx * ty

    # Check if any corner with non-zero weight is None
    corners = [(w00, v00), (w10, v10), (w01, v01), (w11, v11)]
    for w, v in corners:
        if w > 1e-9 and v is None:
            return None

    result = 0.0
    for w, v in corners:
        if w > 1e-9 and v is not None:
            result += w * v

    return result

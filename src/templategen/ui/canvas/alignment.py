"""Pure-math alignment operations for a set of canvas points."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Sequence

Point = tuple[float, float]


def align_horizontal(points: Sequence[Point]) -> list[Point]:
    if not points:
        return []
    avg_y = sum(p[1] for p in points) / len(points)
    return [(p[0], avg_y) for p in points]


def align_vertical(points: Sequence[Point]) -> list[Point]:
    if not points:
        return []
    avg_x = sum(p[0] for p in points) / len(points)
    return [(avg_x, p[1]) for p in points]


def align_line(points: Sequence[Point]) -> list[Point]:
    """Project every point onto the line through the two farthest-apart points."""
    n = len(points)
    if n < 2:
        return list(points)

    i_far, j_far = 0, 1
    best = -1.0
    for i in range(n):
        for j in range(i + 1, n):
            dx = points[i][0] - points[j][0]
            dy = points[i][1] - points[j][1]
            d = dx * dx + dy * dy
            if d > best:
                best = d
                i_far, j_far = i, j

    ax, ay = points[i_far]
    bx, by = points[j_far]
    vx, vy = bx - ax, by - ay
    v_sq = vx * vx + vy * vy
    if v_sq < 1e-12:
        return list(points)

    result: list[Point] = []
    for idx, (px, py) in enumerate(points):
        if idx in (i_far, j_far):
            result.append((px, py))
            continue
        t = ((px - ax) * vx + (py - ay) * vy) / v_sq
        result.append((ax + t * vx, ay + t * vy))
    return result


def distribute_x(points: Sequence[Point]) -> list[Point]:
    """Keep min-X and max-X points; redistribute the rest at equal X spacing."""
    n = len(points)
    if n < 2:
        return list(points)
    order = sorted(range(n), key=lambda i: points[i][0])
    x_min = points[order[0]][0]
    x_max = points[order[-1]][0]
    step = (x_max - x_min) / (n - 1)
    out = list(points)
    for rank, idx in enumerate(order):
        out[idx] = (x_min + rank * step, points[idx][1])
    return out


def distribute_y(points: Sequence[Point]) -> list[Point]:
    """Keep min-Y and max-Y points; redistribute the rest at equal Y spacing."""
    n = len(points)
    if n < 2:
        return list(points)
    order = sorted(range(n), key=lambda i: points[i][1])
    y_min = points[order[0]][1]
    y_max = points[order[-1]][1]
    step = (y_max - y_min) / (n - 1)
    out = list(points)
    for rank, idx in enumerate(order):
        out[idx] = (points[idx][0], y_min + rank * step)
    return out


def distribute_along_line(points: Sequence[Point]) -> list[Point]:
    """Keep the two farthest-apart points; redistribute the rest evenly along the line through them."""
    n = len(points)
    if n < 2:
        return list(points)

    i_far, j_far = 0, 1
    best = -1.0
    for i in range(n):
        for j in range(i + 1, n):
            dx = points[i][0] - points[j][0]
            dy = points[i][1] - points[j][1]
            d = dx * dx + dy * dy
            if d > best:
                best = d
                i_far, j_far = i, j

    ax, ay = points[i_far]
    bx, by = points[j_far]
    vx, vy = bx - ax, by - ay
    v_sq = vx * vx + vy * vy
    if v_sq < 1e-12:
        return list(points)

    t_values = [((px - ax) * vx + (py - ay) * vy) / v_sq for px, py in points]
    order = sorted(range(n), key=lambda i: t_values[i])
    t_lo = t_values[order[0]]
    t_hi = t_values[order[-1]]
    step = (t_hi - t_lo) / (n - 1)

    out: list[Point] = [(0.0, 0.0)] * n
    for rank, idx in enumerate(order):
        t = t_lo + rank * step
        out[idx] = (ax + t * vx, ay + t * vy)
    return out


def align_circle(points: Sequence[Point]) -> list[Point]:
    """Fit the geometric least-squares circle and project each point onto it."""
    n = len(points)
    if n < 3:
        return list(points)

    import numpy as np
    from scipy.optimize import least_squares

    pts = np.asarray(points, dtype=float)

    coef = np.column_stack([2.0 * pts[:, 0], 2.0 * pts[:, 1], np.ones(n)])
    rhs = pts[:, 0] ** 2 + pts[:, 1] ** 2
    sol, *_ = np.linalg.lstsq(coef, rhs, rcond=None)
    cx0, cy0, c0 = sol
    r0 = float(np.sqrt(max(c0 + cx0 * cx0 + cy0 * cy0, 1e-9)))

    def residuals(params: np.ndarray) -> np.ndarray:
        cx, cy, r = params
        return np.sqrt((pts[:, 0] - cx) ** 2 + (pts[:, 1] - cy) ** 2) - r

    result = least_squares(residuals, [cx0, cy0, r0])
    cx, cy, r = (float(v) for v in result.x)
    if r <= 0:
        return list(points)

    out: list[Point] = []
    for px, py in points:
        dx, dy = px - cx, py - cy
        d = (dx * dx + dy * dy) ** 0.5
        if d < 1e-9:
            out.append((px, py))
        else:
            scale = r / d
            out.append((cx + dx * scale, cy + dy * scale))
    return out

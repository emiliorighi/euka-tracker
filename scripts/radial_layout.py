#!/usr/bin/env python3
"""
Radial layout – exact Lifemap algorithm from layout-instructions.md §3.
Eukaryota as root. No modifications to the original formulas.
"""

from __future__ import annotations

import math
import sys
from typing import Any

sys.setrecursionlimit(5000)

ROOT_X = -6.0
ROOT_Y = 9.660254 - 10.0          # -0.339746
ROOT_ALPHA = 150.0
ROOT_RAY = 10.0
ZOOM_CONST = 30.0
POLY_N = 10
MIN_NBDESC_FOR_POLYGON = 3


def _rad(deg: float) -> float:
    return deg * math.pi / 180.0


def _count_descendants(node: dict) -> int:
    if "nbdesc" in node:
        return node["nbdesc"]
    n = 1
    for c in node.get("children") or []:
        n += _count_descendants(c)
    node["nbdesc"] = n
    return n


# ── Polygon construction (§4.3) ─────────────────────────────────────────────

def _half_circle(x, y, r, start, end, n=POLY_N):
    pts = []
    for i in range(n):
        t = start + (end - start) * i / (n - 1) if n > 1 else start
        pts.append((x + r * math.cos(t), y + r * math.sin(t)))
    return pts


def _ellipse(x, y, r, alpha_rad, n=POLY_N):
    a, b = r, r / 6.0
    ca, sa = math.cos(alpha_rad), math.sin(alpha_rad)
    pts = []
    for i in range(n):
        t = math.pi * i / (n - 1) if n > 1 else 0.0
        ct, st = math.cos(t), math.sin(t)
        pts.append((x + a * ct * ca - b * st * sa,
                     y + a * ct * sa + b * st * ca))
    return pts


def _make_polygon(x, y, r, alpha_deg):
    ar = _rad(alpha_deg)
    hc = _half_circle(x, y, r, ar + math.pi / 2, ar - math.pi / 2, POLY_N)
    el = _ellipse(x, y, r, ar, POLY_N)
    return hc + el


# ── Layout pass (§3.3 – verbatim from layout-instructions.md) ──────────────

def _layout(node: dict) -> None:
    children = node.get("children") or []
    if not children:
        return

    ray = node["ray"]
    nbdesc = node["nbdesc"]
    n_children = len(children)

    # §3.3.2  Angle allocation
    tot = sum(math.sqrt(_count_descendants(ch)) for ch in children)
    if tot <= 0:
        tot = 1.0
    for ch in children:
        ch["ang"] = 180.0 * (math.sqrt(_count_descendants(ch)) / tot) / 2.0

    # §3.3.3  Special single-child cases
    special = 0
    if n_children == 1 and nbdesc > 1:
        special = 1
    elif n_children == 1 and nbdesc == 1:
        special = 2

    # §3.3.4  Child ray & dist
    for ch in children:
        if special == 1:
            ch["ray"] = ray - (ray * 20) / 100
        elif special == 2:
            ch["ray"] = ray - (ray * 50) / 100
        else:
            tan_ang = math.sin(_rad(ch["ang"])) / math.cos(_rad(ch["ang"]))
            ch["ray"] = (ray * tan_ang) / (1.0 + tan_ang)
        ch["dist"] = ray - ch["ray"]

    # §3.3.5  Cumulative angles
    angles = [ch["ang"] for ch in children]
    ang_doubled = []
    for a in angles:
        ang_doubled.append(a)
        ang_doubled.append(a)
    ang_cumsum = []
    s = 0.0
    for a in ang_doubled:
        s += a
        ang_cumsum.append(s)
    ang_final = [ang_cumsum[2 * i] for i in range(len(angles))]
    ang_final = [a - (90.0 - node["alpha"]) for a in ang_final]

    # §3.3.6  Position & zoomview
    for i, ch in enumerate(children):
        ch["alpha"] = ang_final[i]
        ch["x"] = node["x"] + ch["dist"] * math.cos(_rad(ch["alpha"]))
        ch["y"] = node["y"] + ch["dist"] * math.sin(_rad(ch["alpha"]))
        zv = math.log2(ZOOM_CONST / ch["ray"]) if ch["ray"] > 0 else 0
        ch["zoomview"] = max(0, math.ceil(zv))

    for ch in children:
        _layout(ch)


# ── Public API ───────────────────────────────────────────────────────────────

def radial_layout(
    tree: dict,
    *,
    root_x: float = ROOT_X,
    root_y: float = ROOT_Y,
    root_alpha: float = ROOT_ALPHA,
    root_ray: float = ROOT_RAY,
) -> dict[str, Any]:
    _count_descendants(tree)

    tree["x"] = root_x
    tree["y"] = root_y
    tree["alpha"] = root_alpha
    tree["ray"] = root_ray
    tree["zoomview"] = max(0, math.ceil(math.log2(ZOOM_CONST / root_ray)))

    _layout(tree)

    nodes: list[dict] = []

    def _collect(nd: dict) -> None:
        children = nd.get("children") or []
        is_internal = len(children) > 0

        polygon = None
        clade_center = None
        if is_internal and nd["ray"] > 0 and nd["nbdesc"] >= MIN_NBDESC_FOR_POLYGON:
            poly = _make_polygon(nd["x"], nd["y"], nd["ray"], nd["alpha"])
            polygon = poly
            cx = sum(p[0] for p in poly) / len(poly)
            cy = sum(p[1] for p in poly) / len(poly)
            clade_center = (cx, cy)

        nodes.append({
            "id": nd["id"],
            "name": nd.get("name", str(nd["id"])),
            "rank": nd.get("rank", "no rank"),
            "x": nd["x"],
            "y": nd["y"],
            "alpha": nd.get("alpha", 0),
            "ray": nd["ray"],
            "zoomview": nd.get("zoomview", 0),
            "nbdesc": nd["nbdesc"],
            "polygon": polygon,
            "clade_center": clade_center,
            "rank_line": None,
            "tip": not is_internal,
        })

        for ch in children:
            _collect(ch)

    _collect(tree)
    return {"nodes": nodes, "root_id": tree["id"]}

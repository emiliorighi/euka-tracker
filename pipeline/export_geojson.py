#!/usr/bin/env python3
"""
Export layout to GeoJSON (points, lines, polygons) per layout-instructions.md §4–5.

Points:  node positions + clade centroids (cladecenter=true).
Lines:   branch segments + rank lines (rankname=true, indices 35–44 of polygon).
Polygons: half-circle + ellipse clade wedges.
All features carry ref=2 (Eukaryotes) and tippecanoe:minzoom for progressive zoom.
"""

import json
from pathlib import Path

REF = 2
MINZOOM_OFFSET = 2


def _minzoom(zoomview: int) -> int:
    return max(0, min(zoomview - MINZOOM_OFFSET, 14))


def collect_edges(tree: dict) -> list[tuple[str, str]]:
    """Recursively collect (parent_id, child_id) edges."""
    edges: list[tuple[str, str]] = []
    pid = tree.get("id", "")
    for child in tree.get("children") or []:
        cid = child.get("id", "")
        if pid and cid:
            edges.append((pid, cid))
        edges.extend(collect_edges(child))
    return edges


def export_geojson(
    layout_result: dict,
    node_info: dict[str, dict],
    tree: dict,
    out_dir: Path,
) -> None:
    nodes = layout_result.get("nodes", [])
    nodes_by_id = {str(n["id"]): n for n in nodes}
    edges = collect_edges(tree)

    # ── Points ───────────────────────────────────────────────────────────
    point_features: list[dict] = []
    for n in nodes:
        nid = str(n["id"])
        zv = int(n.get("zoomview", 0))
        base = {
            "id": nid,
            "ref": REF,
            "sci_name": n.get("name", nid),
            "rank": n.get("rank", "no rank"),
            "zoomview": zv,
            "nbdesc": int(n.get("nbdesc", 0)),
            "tip": bool(n.get("tip")),
            "cladecenter": False,
            "tippecanoe:minzoom": _minzoom(zv),
        }
        point_features.append({
            "type": "Feature",
            "geometry": {"type": "Point", "coordinates": [float(n["x"]), float(n["y"])]},
            "properties": dict(base),
        })
        cc = n.get("clade_center")
        if cc:
            props = dict(base)
            props["cladecenter"] = True
            point_features.append({
                "type": "Feature",
                "geometry": {"type": "Point", "coordinates": [float(cc[0]), float(cc[1])]},
                "properties": props,
            })

    # ── Lines ────────────────────────────────────────────────────────────
    line_features: list[dict] = []

    # Branch lines (parent → child)
    for pid, cid in edges:
        pn = nodes_by_id.get(pid)
        cn = nodes_by_id.get(cid)
        if not pn or not cn:
            continue
        zv = int(cn.get("zoomview", 0))
        pname = pn.get("name", pid)
        cname = cn.get("name", cid)
        if float(cn["x"]) >= float(pn["x"]):
            label = f"\u2190 {pname}     -     {cname} \u2192"
        else:
            label = f"\u2192 {cname}     -     {pname} \u2190"
        line_features.append({
            "type": "Feature",
            "geometry": {
                "type": "LineString",
                "coordinates": [
                    [float(pn["x"]), float(pn["y"])],
                    [float(cn["x"]), float(cn["y"])],
                ],
            },
            "properties": {
                "id": str(cid),
                "ref": REF,
                "branch": True,
                "rankname": False,
                "zoomview": zv,
                "name": label,
                "rank": cn.get("rank", "no rank"),
                "tippecanoe:minzoom": _minzoom(zv),
            },
        })

    # Rank lines (polygon ring indices 35–44)
    for n in nodes:
        rl = n.get("rank_line")
        if not rl or len(rl) < 2:
            continue
        zv = int(n.get("zoomview", 0))
        nid = str(n["id"])
        coords = [[float(x), float(y)] for x, y in rl]
        line_features.append({
            "type": "Feature",
            "geometry": {"type": "LineString", "coordinates": coords},
            "properties": {
                "id": nid,
                "ref": REF,
                "branch": False,
                "rankname": True,
                "zoomview": zv,
                "sci_name": n.get("name", nid),
                "rank": n.get("rank", "no rank"),
                "nbdesc": int(n.get("nbdesc", 0)),
                "tippecanoe:minzoom": _minzoom(zv),
            },
        })

    # ── Polygons ─────────────────────────────────────────────────────────
    polygon_features: list[dict] = []
    for n in nodes:
        poly = n.get("polygon")
        if not poly:
            continue
        coords = [[float(x), float(y)] for x, y in poly]
        if coords and coords[0] != coords[-1]:
            coords.append(coords[0])
        zv = int(n.get("zoomview", 0))
        nid = str(n["id"])
        polygon_features.append({
            "type": "Feature",
            "geometry": {"type": "Polygon", "coordinates": [coords]},
            "properties": {
                "id": nid,
                "ref": REF,
                "sci_name": n.get("name", nid),
                "rank": n.get("rank", "no rank"),
                "zoomview": zv,
                "nbdesc": int(n.get("nbdesc", 0)),
                "clade": True,
                "tippecanoe:minzoom": _minzoom(zv),
            },
        })

    # ── Write ────────────────────────────────────────────────────────────
    out_dir.mkdir(parents=True, exist_ok=True)
    for name, features in [
        ("points.geojson", point_features),
        ("lines.geojson", line_features),
        ("polygons.geojson", polygon_features),
    ]:
        fc = {"type": "FeatureCollection", "features": features}
        with open(out_dir / name, "w") as f:
            json.dump(fc, f, separators=(",", ":"))

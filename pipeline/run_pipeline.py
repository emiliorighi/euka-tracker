#!/usr/bin/env python3
"""
Orchestrate the full pipeline:

1. Build tree from ncbi_taxonomy_tree.tsv
2. Compute radial layout
3. Export GeoJSON (points, lines, polygons)
4. Generate vector tiles (tippecanoe per-layer + tile-join)
5. Extract tiles to XYZ directory
6. Build search index
"""

import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.build_tree import build_tree, EUKARYOTA_TAXID
from pipeline.export_geojson import export_geojson
from scripts.radial_layout import radial_layout


LAYERS = ["polygons", "lines", "points"]


def _run(cmd: list[str], label: str) -> bool:
    try:
        subprocess.run(cmd, check=True, capture_output=True, text=True)
        return True
    except FileNotFoundError:
        print(f"  Warning: {cmd[0]} not found – skipping {label}")
        return False
    except subprocess.CalledProcessError as e:
        print(f"  Warning: {label} failed: {e.stderr[:400]}")
        return False


def run_pipeline(
    data_dir: Path,
    output_dir: Path,
    tile_dir: Path,
) -> bool:
    hierarchy_path = data_dir / "ncbi_taxonomy_tree.tsv"
    geojson_dir = output_dir / "geojson"
    build_dir = output_dir / "tile_build"

    if not hierarchy_path.exists():
        print(f"Error: {hierarchy_path} not found", file=sys.stderr)
        return False

    # --- Step 1: Build tree ---
    print("Step 1: Building tree (root=Eukaryota 2759)...")
    built = build_tree(hierarchy_path, root_id=EUKARYOTA_TAXID)
    tree = built["tree"]
    node_info = built["nodes"]
    print(f"  Root: {built['root_id']} (Eukaryota), nodes: {len(node_info)}")

    # --- Step 2: Radial layout ---
    print("Step 2: Computing radial layout...")
    layout_result = radial_layout(tree)
    layout_nodes = layout_result["nodes"]
    print(f"  Layout nodes: {len(layout_nodes)}")

    # --- Step 3: Export GeoJSON ---
    print("Step 3: Exporting GeoJSON...")
    export_geojson(layout_result, node_info, tree, geojson_dir)
    for name in LAYERS:
        p = geojson_dir / f"{name}.geojson"
        if p.exists():
            sz = p.stat().st_size / (1024 * 1024)
            print(f"  {p.name}: {sz:.1f} MB")

    # --- Step 4: Generate vector tiles (per-layer + tile-join) ---
    print("Step 4: Generating vector tiles...")
    build_dir.mkdir(parents=True, exist_ok=True)
    tile_dir.mkdir(parents=True, exist_ok=True)

    max_zoom = {"polygons": "8", "lines": "10", "points": "10"}
    extra_args = {"polygons": ["--simplification=10"]}

    layer_mbtiles = []
    for layer in LAYERS:
        src = geojson_dir / f"{layer}.geojson"
        dst = build_dir / f"{layer}.mbtiles"
        if not src.exists():
            continue
        mz = max_zoom.get(layer, "10")
        print(f"  tippecanoe: {layer} (z0-{mz})...")
        cmd = [
            "tippecanoe", "--force",
            "-o", str(dst),
            "-z", mz, "-Z", "0",
            "-l", layer,
            "--drop-densest-as-needed",
        ] + extra_args.get(layer, []) + [str(src)]
        ok = _run(cmd, f"tippecanoe ({layer})")
        if ok:
            layer_mbtiles.append(str(dst))

    if not layer_mbtiles:
        print("  No tiles generated (tippecanoe missing or failed)")
    else:
        merged = output_dir / "tiles.mbtiles"
        print(f"  tile-join: merging {len(layer_mbtiles)} layers...")
        if not _run(
            ["tile-join", "--force", "--no-tile-size-limit", "-o", str(merged)] + layer_mbtiles,
            "tile-join",
        ):
            if len(layer_mbtiles) == 1:
                shutil.copy2(layer_mbtiles[0], str(merged))
            else:
                print("  tile-join failed; tiles not merged")

        # --- Step 5: Extract to XYZ ---
        if merged.exists():
            print("Step 5: Extracting tiles to XYZ...")
            if not _run(
                ["mb-util", "--image_format=pbf", str(merged), str(tile_dir)],
                "mb-util",
            ):
                print("  Trying Python extractor...")
                extract_script = Path(__file__).resolve().parent.parent / "scripts" / "extract_tiles.py"
                if extract_script.exists():
                    _run(["python3", str(extract_script)], "extract_tiles.py")
                else:
                    print(f"  Tiles in {merged}")

    # --- Step 6: Search index ---
    print("Step 6: Building search index...")
    search_docs = []
    for n in layout_nodes:
        info = node_info.get(str(n.get("id", "")), {})
        name = info.get("name", str(n.get("id", "")))
        rank = info.get("rank", "no rank")
        doc_id = str(n["id"])
        all_text = f"{name} | {info.get('common_name', '')} | {rank} | {doc_id}"
        search_docs.append([
            doc_id,
            name,
            all_text,
            float(n["x"]),
            float(n["y"]),
            int(n.get("zoomview", 5)),
            rank,
        ])
    search_path = output_dir / "search_index.json"
    with open(search_path, "w") as f:
        json.dump(search_docs, f, separators=(",", ":"))
    print(f"  {search_path}: {len(search_docs)} documents")

    print("Done.")
    return True


def main():
    repo = Path(__file__).resolve().parent.parent
    success = run_pipeline(
        data_dir=repo / "data",
        output_dir=repo / "output",
        tile_dir=repo / "tiles",
    )
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

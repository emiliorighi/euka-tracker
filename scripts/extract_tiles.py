#!/usr/bin/env python3
"""Extract PBF tiles from mbtiles (fallback when mb-util is not installed)."""
import gzip
import sqlite3
import sys
from pathlib import Path


def _decompress(data: bytes) -> bytes:
    """Decompress if gzipped, else return as-is."""
    if len(data) >= 2 and data[:2] == b"\x1f\x8b":
        return gzip.decompress(data)
    return data


def extract(mbtiles: Path, out_dir: Path) -> int:
    """Extract tiles from mbtiles to out_dir/{z}/{x}/{y}.pbf. Returns count."""
    out_dir = Path(out_dir)
    conn = sqlite3.connect(mbtiles)
    cur = conn.execute(
        "SELECT zoom_level, tile_column, tile_row, tile_data FROM tiles"
    )
    count = 0
    for z, x, y_tms, data in cur:
        # mbtiles uses TMS (Y flipped): y_xyz = 2^z - 1 - y_tms
        y = (1 << z) - 1 - y_tms
        tile_path = out_dir / str(z) / str(x) / f"{y}.pbf"
        tile_path.parent.mkdir(parents=True, exist_ok=True)
        tile_path.write_bytes(_decompress(data))
        count += 1
    conn.close()
    return count


def main():
    repo = Path(__file__).resolve().parent.parent
    mbtiles = repo / "output" / "tiles.mbtiles"
    out_dir = repo / "tiles"

    if not mbtiles.exists():
        print(f"Error: {mbtiles} not found", file=sys.stderr)
        sys.exit(1)

    out_dir.mkdir(parents=True, exist_ok=True)
    tiles_json = out_dir / "tiles.json"
    tiles_json_backup = tiles_json.read_bytes() if tiles_json.exists() else None

    print(f"Extracting from {mbtiles}...")
    n = extract(mbtiles, out_dir)
    print(f"Extracted {n} tiles to {out_dir}/")

    if tiles_json_backup:
        tiles_json.write_bytes(tiles_json_backup)

    return 0


if __name__ == "__main__":
    sys.exit(main())

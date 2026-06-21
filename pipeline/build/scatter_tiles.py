"""Build deepscatter tile pyramid from IUCN scatter parquet via quadfeather."""

from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path

import pyarrow.feather as feather

from pipeline.patch_tile_metadata import patch_tile_metadata

PIPELINE_DIR = Path(__file__).resolve().parents[1]
DEFAULT_PARQUET = PIPELINE_DIR / "output" / "iucn_species_scatter.parquet"
TILE_SIZE = 50_000


def tile_version_for(day: date | None = None) -> str:
    d = day or date.today()
    return f"v{d.strftime('%Y%m%d')}"


def _find_quadfeather() -> str:
    exe = shutil.which("quadfeather")
    if exe:
        return exe
    # Same venv as `python -m pipeline.build.scatter_tiles`
    venv_bin = Path(sys.executable).resolve().parent / "quadfeather"
    if venv_bin.is_file():
        return str(venv_bin)
    # sys.executable may be a shim; try adjacent to real interpreter
    import sysconfig

    scripts_dir = Path(sysconfig.get_path("scripts"))
    scripts_exe = scripts_dir / "quadfeather"
    if scripts_exe.is_file():
        return str(scripts_exe)
    raise FileNotFoundError(
        "quadfeather not found on PATH. Install with:\n"
        "  pip install git+https://github.com/bmschmidt/quadfeather"
    )


def build_scatter_tiles(
    *,
    parquet_path: Path = DEFAULT_PARQUET,
    destination: Path | None = None,
    version: str | None = None,
    tile_size: int = TILE_SIZE,
) -> Path:
    if not parquet_path.is_file():
        raise FileNotFoundError(
            f"Scatter parquet not found: {parquet_path}. Run pipeline.build.scatter_layout first."
        )

    ver = version or tile_version_for()
    dest = destination or (PIPELINE_DIR / "output" / "tiles" / "iucn" / ver)
    if dest.exists():
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=True)

    quadfeather = _find_quadfeather()
    cmd = [
        quadfeather,
        "--files",
        str(parquet_path),
        "--tile_size",
        str(tile_size),
        "--destination",
        str(dest),
    ]
    print(f"Running: {' '.join(cmd)}", file=sys.stderr)
    subprocess.run(cmd, check=True)

    root_tile = dest / "0" / "0" / "0.feather"
    if not root_tile.is_file():
        raise FileNotFoundError(f"quadfeather did not produce root tile at {root_tile}")

    table = feather.read_table(root_tile)
    xs = table.column("x").to_pylist()
    ys = table.column("y").to_pylist()
    extent = {
        "x": [min(xs), max(xs)],
        "y": [min(ys), max(ys)],
    }
    (dest / "view_extent.json").write_text(json.dumps(extent) + "\n", encoding="utf-8")

    patched = patch_tile_metadata(dest)
    print(f"Patched extent/children metadata on {patched} tiles", file=sys.stderr)

    print(f"Wrote tile pyramid to {dest}", file=sys.stderr)
    return dest


def main() -> None:
    parser = argparse.ArgumentParser(description="Build IUCN scatter tiles with quadfeather")
    parser.add_argument("--parquet", type=Path, default=DEFAULT_PARQUET)
    parser.add_argument("--destination", type=Path, default=None)
    parser.add_argument("--version", default=None, help="Tile version folder, e.g. v20260620")
    parser.add_argument("--tile-size", type=int, default=TILE_SIZE)
    parser.add_argument(
        "--patch-only",
        type=Path,
        metavar="TILE_DIR",
        help="Patch extent/children metadata on an existing tile pyramid (no quadfeather rebuild)",
    )
    args = parser.parse_args()
    if args.patch_only is not None:
        patched = patch_tile_metadata(args.patch_only)
        print(f"Patched extent/children metadata on {patched} tiles", file=sys.stderr)
        return
    build_scatter_tiles(
        parquet_path=args.parquet,
        destination=args.destination,
        version=args.version,
        tile_size=args.tile_size,
    )


if __name__ == "__main__":
    main()

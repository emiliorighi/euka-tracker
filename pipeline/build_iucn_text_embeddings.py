#!/usr/bin/env python3
"""Build per-field IUCN text embedding caches (sentence-transformers + PCA)."""

from __future__ import annotations

import argparse
import random
import sys
from pathlib import Path
from typing import Any

import numpy as np

_REPO = Path(__file__).resolve().parent.parent
if str(_REPO) not in sys.path:
    sys.path.insert(0, str(_REPO))

from pipeline.iucn_assessments_convert import IUCN_TEXT_FIELDS  # noqa: E402
from pipeline.iucn_text_embeddings import (  # noqa: E402
    DEFAULT_MODEL,
    SUPPORTED_MODELS,
    build_field_feature_matrix,
    load_taxid_order,
    model_slug,
    read_json,
    save_pca,
    tsv_mtime,
    write_json,
)

DEFAULT_IUCN = _REPO / "data" / "iucn_assessments.tsv"
DEFAULT_CACHE = _REPO / "data" / "cache" / "iucn_text_embeddings"
DEFAULT_FIELDS = ("threats",)


def _parse_fields(raw: str | None) -> list[str]:
    if not raw:
        return list(DEFAULT_FIELDS)
    fields = [f.strip() for f in raw.split(",") if f.strip()]
    bad = [f for f in fields if f not in IUCN_TEXT_FIELDS]
    if bad:
        raise SystemExit(
            f"Unknown --fields: {bad}. Expected subset of {list(IUCN_TEXT_FIELDS)}"
        )
    return fields


def _field_paths(cache_dir: Path, field: str, model: str, pca_dims: int) -> dict[str, Path]:
    slug = model_slug(model)
    field_dir = cache_dir / field
    return {
        "dir": field_dir,
        "embeddings": field_dir / f"embeddings_{slug}.npy",
        "pca": field_dir / f"pca_{slug}_{pca_dims}.npz",
        "features": field_dir / f"features_{slug}_{pca_dims}.npy",
        "manifest": field_dir / "field_manifest.json",
    }


def _cache_valid(
    paths: dict[str, Path],
    *,
    field: str,
    model: str,
    pca_dims: int,
    iucn_mtime: float,
    require_embeddings: bool,
) -> bool:
    manifest_path = paths["manifest"]
    if not manifest_path.is_file():
        return False
    manifest = read_json(manifest_path)
    if manifest.get("field") != field:
        return False
    if manifest.get("model") != model:
        return False
    if manifest.get("pca_dims") != pca_dims:
        return False
    if manifest.get("iucn_mtime") != iucn_mtime:
        return False
    if not paths["features"].is_file():
        return False
    if require_embeddings and not paths["embeddings"].is_file():
        return False
    if not paths["pca"].is_file():
        return False
    return True


def _print_qa(
    field: str,
    taxids: np.ndarray,
    has_text: np.ndarray,
    features: np.ndarray,
    meta: dict[str, Any],
) -> None:
    n = len(taxids)
    n_text = int(has_text.sum())
    pct = 100.0 * n_text / max(n, 1)
    print(f"  {field}: {n:,} taxids, {n_text:,} with text ({pct:.1f}%)", file=sys.stderr)
    evr = meta.get("explained_variance_ratio_sum", 0.0)
    print(f"  PCA explained variance (sum top {meta.get('pca_dims', '?')}): {evr:.3f}", file=sys.stderr)
    if pct < 50:
        print(f"  Warning: {field} has_text < 50%", file=sys.stderr)

    if n_text > 0:
        rng = random.Random(42)
        sample_idx = rng.sample(range(n), min(3, n))
        for i in sample_idx:
            tid = int(taxids[i])
            ht = int(has_text[i])
            f0 = float(features[i, 0]) if features.shape[1] else 0.0
            print(f"  spot-check taxid={tid} has_text={ht} feature[0]={f0:.4f}", file=sys.stderr)


def run_field(
    field: str,
    *,
    iucn_tsv: Path,
    cache_dir: Path,
    taxids: list[int],
    model: Any,
    model_name: str,
    pca_dims: int,
    batch_size: int,
    force: bool,
    skip_embed: bool,
    iucn_mtime_val: float,
) -> None:
    paths = _field_paths(cache_dir, field, model_name, pca_dims)
    paths["dir"].mkdir(parents=True, exist_ok=True)

    if not force and _cache_valid(
        paths,
        field=field,
        model=model_name,
        pca_dims=pca_dims,
        iucn_mtime=iucn_mtime_val,
        require_embeddings=not skip_embed,
    ):
        print(f"Cache hit for {field} — skipping", file=sys.stderr)
        manifest = read_json(paths["manifest"])
        taxids_arr = np.load(cache_dir / "taxids.npy")
        has_text = np.load(paths["dir"] / "has_text.npy")
        features = np.load(paths["features"])
        _print_qa(field, taxids_arr, has_text, features, manifest)
        return

    print(f"Building embeddings for {field}…", file=sys.stderr)
    embeddings: np.ndarray | None = None
    if skip_embed and paths["embeddings"].is_file():
        embeddings = np.load(paths["embeddings"])
        print(f"  Reusing {paths['embeddings']}", file=sys.stderr)
    elif not skip_embed and paths["embeddings"].is_file() and not force:
        embeddings = np.load(paths["embeddings"])
        print(f"  Reusing cached embeddings {paths['embeddings']}", file=sys.stderr)

    features, embeddings, has_text, meta, fitted_pca = build_field_feature_matrix(
        iucn_tsv,
        field,
        taxids,
        model_name=model_name,
        pca_dims=pca_dims,
        batch_size=batch_size,
        model=model,
        embeddings=embeddings,
    )

    np.save(paths["embeddings"], embeddings)
    np.save(paths["features"], features)
    np.save(paths["dir"] / "has_text.npy", has_text)

    save_pca(fitted_pca, paths["pca"])

    manifest = {
        **meta,
        "iucn_mtime": iucn_mtime_val,
        "iucn_tsv": str(iucn_tsv),
    }
    write_json(paths["manifest"], manifest)
    _print_qa(field, np.asarray(taxids), has_text, features, manifest)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build per-field IUCN text embedding caches"
    )
    parser.add_argument(
        "--iucn",
        type=Path,
        default=DEFAULT_IUCN,
        help=f"IUCN assessments TSV (default: {DEFAULT_IUCN})",
    )
    parser.add_argument(
        "--cache-dir",
        type=Path,
        default=DEFAULT_CACHE,
        help=f"Cache root (default: {DEFAULT_CACHE})",
    )
    parser.add_argument(
        "--fields",
        type=str,
        default=None,
        help=f"Comma-separated fields (default: {list(DEFAULT_FIELDS)}; "
        f"also supported: {list(IUCN_TEXT_FIELDS)})",
    )
    parser.add_argument(
        "--model",
        type=str,
        default=DEFAULT_MODEL,
        choices=SUPPORTED_MODELS,
        help="sentence-transformers model",
    )
    parser.add_argument("--pca-dims", type=int, default=32, help="PCA dims per field")
    parser.add_argument("--batch-size", type=int, default=256, help="Encode batch size")
    parser.add_argument("--force", action="store_true", help="Re-embed even if cache valid")
    parser.add_argument(
        "--skip-embed",
        action="store_true",
        help="Reuse raw embeddings; re-run PCA + features only",
    )
    args = parser.parse_args()

    if not args.iucn.is_file():
        print(f"Error: IUCN TSV not found: {args.iucn}", file=sys.stderr)
        return 1

    fields = _parse_fields(args.fields)
    iucn_mtime_val = tsv_mtime(args.iucn)
    taxids = load_taxid_order(args.iucn)
    if not taxids:
        print("Error: no taxids with resolved NCBI mapping in TSV", file=sys.stderr)
        return 1

    args.cache_dir.mkdir(parents=True, exist_ok=True)
    np.save(args.cache_dir / "taxids.npy", np.asarray(taxids, dtype=np.int64))

    st_model: Any | None = None
    if not args.skip_embed:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError:
            print(
                "Error: sentence-transformers not installed. "
                "Run: pipenv install sentence-transformers",
                file=sys.stderr,
            )
            return 1
        print(
            f"Loading model {args.model} (first run downloads weights to "
            "~/.cache/torch/sentence_transformers/)…",
            file=sys.stderr,
        )
        st_model = SentenceTransformer(args.model)

    print(
        f"IUCN text embeddings: {len(taxids):,} taxids, fields={fields}, "
        f"model={args.model}, pca_dims={args.pca_dims}",
        file=sys.stderr,
    )

    for field in fields:
        run_field(
            field,
            iucn_tsv=args.iucn,
            cache_dir=args.cache_dir,
            taxids=taxids,
            model=st_model,
            model_name=args.model,
            pca_dims=args.pca_dims,
            batch_size=args.batch_size,
            force=args.force,
            skip_embed=args.skip_embed,
            iucn_mtime_val=iucn_mtime_val,
        )

    write_json(
        args.cache_dir / "manifest.json",
        {
            "model": args.model,
            "pca_dims": args.pca_dims,
            "iucn_mtime": iucn_mtime_val,
            "iucn_tsv": str(args.iucn),
            "n_taxids": len(taxids),
            "fields": fields,
        },
    )
    print(f"Done → {args.cache_dir}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Per-field IUCN assessment text embeddings (sentence-transformers + PCA)."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any

import numpy as np

from pipeline.iucn_assessments_convert import IUCN_TEXT_FIELDS
from pipeline.landscape_features import standardize_features

DEFAULT_MODEL = "all-MiniLM-L6-v2"
SUPPORTED_MODELS = (DEFAULT_MODEL, "all-mpnet-base-v2")
MODEL_DIMS = {
    DEFAULT_MODEL: 384,
    "all-mpnet-base-v2": 768,
}


def model_slug(model_name: str) -> str:
    return model_name.replace("/", "_")


def load_taxid_order(iucn_tsv: Path) -> list[int]:
    """Return taxids in TSV row order (rows with resolved taxid only)."""
    taxids: list[int] = []
    seen: set[int] = set()
    with open(iucn_tsv, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            raw = (row.get("taxid") or "").strip()
            if not raw:
                continue
            try:
                taxid = int(raw)
            except ValueError:
                continue
            if taxid in seen:
                continue
            seen.add(taxid)
            taxids.append(taxid)
    return taxids


def load_text_by_taxid(iucn_tsv: Path, field: str) -> dict[int, str]:
    """Stream TSV → taxid → text for one field (last row wins on duplicates)."""
    if field not in IUCN_TEXT_FIELDS:
        raise ValueError(f"Unknown field {field!r}; expected one of {IUCN_TEXT_FIELDS}")
    records: dict[int, str] = {}
    with open(iucn_tsv, encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f, delimiter="\t"):
            raw = (row.get("taxid") or "").strip()
            if not raw:
                continue
            try:
                taxid = int(raw)
            except ValueError:
                continue
            text = (row.get(field) or "").strip()
            if text:
                records[taxid] = text
    return records


def texts_for_taxids(taxids: list[int], text_by_taxid: dict[int, str]) -> list[str]:
    return [text_by_taxid.get(taxid, "") for taxid in taxids]


def encode_texts(
    texts: list[str],
    model_name: str,
    *,
    batch_size: int = 256,
    model: Any | None = None,
) -> np.ndarray:
    """Encode texts; empty strings become zero vectors without model calls."""
    dim = MODEL_DIMS.get(model_name)
    if dim is None:
        raise ValueError(f"Unsupported model {model_name!r}; use one of {SUPPORTED_MODELS}")

    n = len(texts)
    out = np.zeros((n, dim), dtype=np.float32)
    non_empty_idx: list[int] = []
    non_empty_texts: list[str] = []
    for i, text in enumerate(texts):
        if text.strip():
            non_empty_idx.append(i)
            non_empty_texts.append(text)

    if not non_empty_texts:
        return out

    if model is None:
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is required. Install with: pipenv install sentence-transformers"
            ) from exc
        model = SentenceTransformer(model_name)

    encoded = model.encode(
        non_empty_texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
    )
    out[np.asarray(non_empty_idx, dtype=np.int64)] = np.asarray(encoded, dtype=np.float32)
    return out


def fit_and_transform_pca(
    embeddings: np.ndarray,
    has_text: np.ndarray,
    *,
    n_components: int = 32,
) -> tuple[np.ndarray, Any, dict[str, float]]:
    """
    Fit PCA on rows with non-zero embeddings; zero rows stay zero after transform.

    Returns (pca_features, fitted_pca, stats).
    """
    from sklearn.decomposition import PCA

    n, dim = embeddings.shape
    n_components = min(n_components, dim)
    out = np.zeros((n, n_components), dtype=np.float32)

    mask = has_text.astype(bool)
    if mask.sum() < 2:
        return out, None, {"explained_variance_ratio_sum": 0.0, "n_fit_rows": int(mask.sum())}

    pca = PCA(n_components=n_components, random_state=42)
    reduced = pca.fit_transform(embeddings[mask])
    out[mask] = reduced.astype(np.float32)

    evr_sum = float(np.sum(pca.explained_variance_ratio_))
    stats = {
        "explained_variance_ratio_sum": evr_sum,
        "n_fit_rows": int(mask.sum()),
        "explained_variance_ratio": [float(x) for x in pca.explained_variance_ratio_],
    }
    return out, pca, stats


def build_field_feature_matrix(
    iucn_tsv: Path,
    field: str,
    taxids: list[int],
    *,
    model_name: str = DEFAULT_MODEL,
    pca_dims: int = 32,
    batch_size: int = 256,
    model: Any | None = None,
    embeddings: np.ndarray | None = None,
) -> tuple[np.ndarray, np.ndarray, np.ndarray, dict[str, Any], Any]:
    """
    Build z-scored PCA features for one field.

    Returns (features_z, raw_embeddings, has_text_mask, metadata, fitted_pca).
    """
    text_by_taxid = load_text_by_taxid(iucn_tsv, field)
    texts = texts_for_taxids(taxids, text_by_taxid)
    has_text = np.array([1 if t.strip() else 0 for t in texts], dtype=np.int8)

    if embeddings is None:
        embeddings = encode_texts(texts, model_name, batch_size=batch_size, model=model)
    else:
        if embeddings.shape[0] != len(taxids):
            raise ValueError(
                f"embeddings rows {embeddings.shape[0]} != taxids {len(taxids)}"
            )

    pca_raw, pca, pca_stats = fit_and_transform_pca(
        embeddings, has_text, n_components=pca_dims
    )
    features_z = standardize_features(pca_raw.astype(np.float64)).astype(np.float32)

    meta: dict[str, Any] = {
        "field": field,
        "model": model_name,
        "pca_dims": pca_dims,
        "n_taxids": len(taxids),
        "n_has_text": int(has_text.sum()),
        "pct_has_text": round(100.0 * float(has_text.sum()) / max(len(taxids), 1), 2),
        **pca_stats,
    }
    return features_z, embeddings, has_text, meta, pca


def tsv_mtime(iucn_tsv: Path) -> float:
    return iucn_tsv.stat().st_mtime


def save_pca(pca: Any, path: Path) -> None:
    if pca is None:
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    np.savez(
        path,
        components_=pca.components_,
        mean_=pca.mean_,
        explained_variance_ratio_=pca.explained_variance_ratio_,
    )


def load_pca(path: Path) -> Any:
    from sklearn.decomposition import PCA

    data = np.load(path)
    n_components = data["components_"].shape[0]
    pca = PCA(n_components=n_components, random_state=42)
    pca.components_ = data["components_"]
    pca.mean_ = data["mean_"]
    pca.explained_variance_ratio_ = data["explained_variance_ratio_"]
    return pca


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def load_threat_features_by_taxid(
    cache_dir: Path,
    *,
    model_name: str = DEFAULT_MODEL,
    pca_dims: int = 32,
) -> dict[int, np.ndarray]:
    """Load z-scored threats PCA rows keyed by taxid (zero vector if missing)."""
    slug = model_slug(model_name)
    taxids_path = cache_dir / "taxids.npy"
    features_path = cache_dir / "threats" / f"features_{slug}_{pca_dims}.npy"
    if not taxids_path.is_file():
        raise FileNotFoundError(f"Threat cache taxids not found: {taxids_path}")
    if not features_path.is_file():
        raise FileNotFoundError(f"Threat PCA features not found: {features_path}")

    taxids = np.load(taxids_path)
    features = np.load(features_path)
    if features.shape[0] != taxids.shape[0]:
        raise ValueError(
            f"Threat features rows {features.shape[0]} != taxids {taxids.shape[0]}"
        )

    dim = features.shape[1]
    zero = np.zeros(dim, dtype=np.float32)
    out: dict[int, np.ndarray] = {}
    for i, raw_taxid in enumerate(taxids):
        taxid = int(raw_taxid)
        out[taxid] = features[i].astype(np.float32)
    out.setdefault(0, zero)
    return out


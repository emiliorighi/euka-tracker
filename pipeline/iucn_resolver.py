"""IUCN-centric resolution against GBIF, iNaturalist, and NCBI taxonomy + genomic evidence."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from pipeline.load_iucn_species import IucnSpecies
from pipeline.match_keys import binom_key, norm_key
from pipeline.schema import READ_FLAG_FIELDS
from pipeline.ncbi_evidence import NcbiEvidenceIndex, NcbiNameIndex, SpeciesEvidence

DEFAULT_CACHE_SIZE = -262144


@dataclass
class ResolvedIucnSpecies:
    has_gbif: bool = False
    has_inat: bool = False
    has_goat: bool = False
    has_assemblies: bool = False
    has_annotations: bool = False
    read_flags: dict[str, bool] = field(default_factory=lambda: {f: False for f in READ_FLAG_FIELDS})
    gbif_id: str = ""
    inat_id: str = ""
    ncbi_taxid: str = ""
    ncbi_match_method: str = ""

    def flag_dict(self) -> dict[str, str]:
        out = {
            "hasGbif": "1" if self.has_gbif else "0",
            "hasInat": "1" if self.has_inat else "0",
            "hasGoat": "1" if self.has_goat else "0",
            "hasAssemblies": "1" if self.has_assemblies else "0",
            "hasAnnotations": "1" if self.has_annotations else "0",
            "ncbiTaxid": self.ncbi_taxid,
            "gbifId": self.gbif_id,
            "inatId": self.inat_id,
            "ncbiMatchMethod": self.ncbi_match_method,
        }
        for flag in READ_FLAG_FIELDS:
            out[flag] = "1" if self.read_flags.get(flag, False) else "0"
        return out


def _aliases(species: IucnSpecies) -> list[str]:
    aliases: list[str] = []
    seen: set[str] = set()
    for candidate in (
        species.scientific_name,
        f"{species.genus_name} {species.species_name}".strip(),
    ):
        key = norm_key(candidate)
        if key and key not in seen:
            seen.add(key)
            aliases.append(key)
    return aliases


def _lineage_ok(
    genus: str,
    family: str,
    order: str,
    phylum: str,
    kingdom: str,
    lineage_tokens: set[str],
    iucn_genus: str,
) -> bool:
    if not iucn_genus:
        return True
    g = (genus or "").strip().lower()
    if g and (g == iucn_genus or g in lineage_tokens):
        return True
    for part in (family, order, phylum, kingdom):
        token = (part or "").strip().lower()
        if token and token in lineage_tokens:
            return True
    return False


def _pick_gbif_rows(
    rows: list[tuple],
    *,
    lineage_tokens: set[str],
    iucn_genus: str,
) -> int | None:
    if not rows:
        return None
    survivors: list[int] = []
    for gid, genus, family, order, phylum, kingdom in rows:
        if _lineage_ok(genus, family, order, phylum, kingdom, lineage_tokens, iucn_genus):
            survivors.append(int(gid))
    unique = sorted(set(survivors))
    if len(unique) == 1:
        return unique[0]
    return None


def _pick_inat_rows(
    rows: list[tuple],
    *,
    lineage_tokens: set[str],
    iucn_genus: str,
) -> int | None:
    if not rows:
        return None
    survivors: list[int] = []
    for iid, genus, family, phylum, kingdom in rows:
        if _lineage_ok(genus, family, "", phylum, kingdom, lineage_tokens, iucn_genus):
            survivors.append(int(iid))
    unique = sorted(set(survivors))
    if len(unique) == 1:
        return unique[0]
    return None


def _pick_ncbi_taxids(
    candidates: set[int],
    name_index: NcbiNameIndex,
    *,
    lineage_tokens: set[str],
    iucn_genus: str,
) -> int | None:
    if not candidates:
        return None
    survivors: list[int] = []
    for taxid in candidates:
        ctx = name_index.lineage_by_taxid.get(taxid)
        if ctx is None:
            survivors.append(taxid)
            continue
        genus, family, order, phylum, kingdom = ctx
        if _lineage_ok(genus, family, order, phylum, kingdom, lineage_tokens, iucn_genus):
            survivors.append(taxid)
    unique = sorted(set(survivors))
    if len(unique) == 1:
        return unique[0]
    return None


def _gbif_rows_for_name(conn: sqlite3.Connection, name_norm: str) -> list[tuple]:
    return conn.execute(
        """SELECT DISTINCT a.gbif_id, a.genus, a.family, a.taxon_order, a.phylum, a.kingdom
           FROM gbif_name n
           JOIN gbif_accepted a ON a.gbif_id = n.gbif_id
           WHERE n.name_norm = ?""",
        (name_norm,),
    ).fetchall()


def _gbif_rows_for_binomial(conn: sqlite3.Connection, bk: str) -> list[tuple]:
    return conn.execute(
        """SELECT DISTINCT a.gbif_id, a.genus, a.family, a.taxon_order, a.phylum, a.kingdom
           FROM gbif_binomial b
           JOIN gbif_accepted a ON a.gbif_id = b.gbif_id
           WHERE b.binom_key = ?""",
        (bk,),
    ).fetchall()


def _inat_rows_for_name(conn: sqlite3.Connection, name_norm: str) -> list[tuple]:
    return conn.execute(
        """SELECT DISTINCT r.inat_id, r.genus, r.family, r.phylum, r.kingdom
           FROM inat_name n
           JOIN inat_record r ON r.inat_id = n.inat_id
           WHERE n.name_norm = ?""",
        (name_norm,),
    ).fetchall()


def _inat_rows_for_binomial(conn: sqlite3.Connection, bk: str) -> list[tuple]:
    return conn.execute(
        """SELECT DISTINCT r.inat_id, r.genus, r.family, r.phylum, r.kingdom
           FROM inat_binomial b
           JOIN inat_record r ON r.inat_id = b.inat_id
           WHERE b.binom_key = ?""",
        (bk,),
    ).fetchall()


def _resolve_gbif(
    conn: sqlite3.Connection,
    species: IucnSpecies,
    aliases: list[str],
) -> int | None:
    lineage_tokens = species.lineage_tokens
    iucn_genus = norm_key(species.genus_name)

    for alias in aliases:
        gbif_id = _pick_gbif_rows(
            _gbif_rows_for_name(conn, alias),
            lineage_tokens=lineage_tokens,
            iucn_genus=iucn_genus,
        )
        if gbif_id is not None:
            return gbif_id

    binomial_keys = {binom_key(alias) for alias in aliases}
    binomial_keys.discard("")
    for bk in sorted(binomial_keys):
        gbif_id = _pick_gbif_rows(
            _gbif_rows_for_binomial(conn, bk),
            lineage_tokens=lineage_tokens,
            iucn_genus=iucn_genus,
        )
        if gbif_id is not None:
            return gbif_id
    return None


def _resolve_inat(
    conn: sqlite3.Connection,
    species: IucnSpecies,
    aliases: list[str],
    *,
    gbif_canonical: str | None = None,
) -> int | None:
    lineage_tokens = species.lineage_tokens
    iucn_genus = norm_key(species.genus_name)

    if gbif_canonical:
        k = norm_key(gbif_canonical)
        if k:
            inat_id = _pick_inat_rows(
                _inat_rows_for_name(conn, k),
                lineage_tokens=lineage_tokens,
                iucn_genus=iucn_genus,
            )
            if inat_id is not None:
                return inat_id
        bk = binom_key(gbif_canonical)
        if bk:
            inat_id = _pick_inat_rows(
                _inat_rows_for_binomial(conn, bk),
                lineage_tokens=lineage_tokens,
                iucn_genus=iucn_genus,
            )
            if inat_id is not None:
                return inat_id

    for alias in aliases:
        inat_id = _pick_inat_rows(
            _inat_rows_for_name(conn, alias),
            lineage_tokens=lineage_tokens,
            iucn_genus=iucn_genus,
        )
        if inat_id is not None:
            return inat_id

    binomial_keys = {binom_key(alias) for alias in aliases}
    binomial_keys.discard("")
    for bk in sorted(binomial_keys):
        inat_id = _pick_inat_rows(
            _inat_rows_for_binomial(conn, bk),
            lineage_tokens=lineage_tokens,
            iucn_genus=iucn_genus,
        )
        if inat_id is not None:
            return inat_id
    return None


def _resolve_ncbi_direct(
    name_index: NcbiNameIndex,
    species: IucnSpecies,
    aliases: list[str],
) -> tuple[int | None, str]:
    lineage_tokens = species.lineage_tokens
    iucn_genus = norm_key(species.genus_name)

    for alias in aliases:
        taxid = name_index.name_to_sp.get(alias)
        if taxid is not None:
            picked = _pick_ncbi_taxids(
                {taxid},
                name_index,
                lineage_tokens=lineage_tokens,
                iucn_genus=iucn_genus,
            )
            if picked is not None:
                return picked, "direct"

    binomial_keys = {binom_key(alias) for alias in aliases}
    binomial_keys.discard("")
    for bk in sorted(binomial_keys):
        candidates = name_index.binom_to_sp.get(bk)
        if not candidates:
            continue
        picked = _pick_ncbi_taxids(
            candidates,
            name_index,
            lineage_tokens=lineage_tokens,
            iucn_genus=iucn_genus,
        )
        if picked is not None:
            return picked, "direct"
    return None, ""


def _apply_evidence(result: ResolvedIucnSpecies, evidence: SpeciesEvidence) -> None:
    result.has_goat = evidence.has_goat
    result.has_assemblies = evidence.has_assemblies
    result.has_annotations = evidence.has_annotations
    result.read_flags = dict(evidence.read_flags)


class IucnResolver:
    def __init__(
        self,
        cross_universe_path: str | Path,
        name_index: NcbiNameIndex,
        evidence: NcbiEvidenceIndex,
        gbif_to_ncbi: dict[int, int],
    ) -> None:
        self._name_index = name_index
        self._evidence = evidence
        self._gbif_to_ncbi = gbif_to_ncbi
        self._conn = sqlite3.connect(str(cross_universe_path))
        self._conn.execute(f"PRAGMA cache_size={DEFAULT_CACHE_SIZE}")

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> IucnResolver:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def resolve(self, species: IucnSpecies) -> ResolvedIucnSpecies:
        result = ResolvedIucnSpecies()
        aliases = _aliases(species)

        gbif_id = _resolve_gbif(self._conn, species, aliases)
        if gbif_id is not None:
            result.has_gbif = True
            result.gbif_id = str(gbif_id)

        gbif_canonical: str | None = None
        if gbif_id is not None:
            row = self._conn.execute(
                "SELECT canonical FROM gbif_accepted WHERE gbif_id = ?",
                (gbif_id,),
            ).fetchone()
            if row and row[0]:
                gbif_canonical = str(row[0])

        inat_id = _resolve_inat(
            self._conn,
            species,
            aliases,
            gbif_canonical=gbif_canonical,
        )
        if inat_id is not None:
            result.has_inat = True
            result.inat_id = str(inat_id)

        ncbi_taxid, method = _resolve_ncbi_direct(self._name_index, species, aliases)
        if ncbi_taxid is None and gbif_id is not None:
            bridged = self._gbif_to_ncbi.get(gbif_id)
            if bridged is not None:
                ncbi_taxid = bridged
                method = "bridge"

        if ncbi_taxid is not None:
            result.ncbi_taxid = str(ncbi_taxid)
            result.ncbi_match_method = method
            species_evidence = self._evidence.evidence_by_taxid.get(ncbi_taxid)
            if species_evidence is not None:
                _apply_evidence(result, species_evidence)

        return result

#!/usr/bin/env node
/**
 * Load slim 06_taxon_rollups.tsv for atlas layout/segment check scripts.
 */
import { readFileSync } from "node:fs"
import { dirname, join } from "node:path"
import { fileURLToPath } from "node:url"

const __dirname = dirname(fileURLToPath(import.meta.url))
const DEFAULT_ROLLUPS = join(__dirname, "../../data/staged/06_taxon_rollups.tsv")

const LEAF_RANKS = new Set(["species", "subspecies", "strain", "varietas", "forma"])
const EUKARYOTA_TAXID = 2759

function pruneOrphanNodes(nodes) {
  let current = nodes
  while (true) {
    const ids = new Set(current.map((n) => n.taxid))
    const remove = new Set()
    for (const node of current) {
      if (node.taxid === EUKARYOTA_TAXID) continue
      const pid = node.parent_taxid
      if (pid && !ids.has(pid)) remove.add(node.taxid)
    }
    if (remove.size === 0) return current
    current = current.filter((n) => !remove.has(n.taxid))
  }
}

const NUMERIC_FIELDS = new Set([
  "taxid",
  "parent_taxid",
  "depth_from_eukaryota",
  "species_count_ncbi",
  "species_count_with_data",
  "species_with_reads",
  "species_with_assembly",
  "species_with_annotations",
  "sum_run_count",
  "sum_assembly_count",
  "sum_annotation_count",
  "landscape_cx",
  "landscape_cy",
  "landscape_bbox_x0",
  "landscape_bbox_x1",
  "landscape_bbox_y0",
  "landscape_bbox_y1",
])

function parseField(key, value) {
  if (NUMERIC_FIELDS.has(key)) {
    const n = value === "" ? 0 : Number(value)
    return Number.isFinite(n) ? n : 0
  }
  return value ?? ""
}

function toTaxonRollupView(node) {
  return {
    ...node,
    species_count_matrix: node.species_count_with_data,
    species_with_annotation: node.species_with_annotations,
  }
}

export function loadAtlasRollups(path = process.env.ATLAS_ROLLUPS_PATH ?? DEFAULT_ROLLUPS) {
  const text = readFileSync(path, "utf8")
  const lines = text.split("\n")
  const headers = lines[0].split("\t")

  const rowById = new Map()
  const childrenByParent = new Map()
  const parsed = []

  for (let i = 1; i < lines.length; i++) {
    const line = lines[i]
    if (!line?.trim()) continue
    const parts = line.split("\t")
    const raw = Object.fromEntries(headers.map((h, c) => [h, parts[c] ?? ""]))
    const rank = String(parseField("rank", raw.rank)).trim().toLowerCase()
    if (LEAF_RANKS.has(rank)) continue

    const node = {
      taxid: Number(parseField("taxid", raw.taxid)),
      parent_taxid: Number(parseField("parent_taxid", raw.parent_taxid)) || 0,
      scientific_name: String(parseField("scientific_name", raw.scientific_name)),
      rank: String(parseField("rank", raw.rank)),
      depth_from_eukaryota: Number(parseField("depth_from_eukaryota", raw.depth_from_eukaryota)) || 0,
      species_count_ncbi: Number(parseField("species_count_ncbi", raw.species_count_ncbi)) || 0,
      species_count_with_data:
        Number(parseField("species_count_with_data", raw.species_count_with_data)) || 0,
      species_with_reads: Number(parseField("species_with_reads", raw.species_with_reads)) || 0,
      species_with_assembly: Number(parseField("species_with_assembly", raw.species_with_assembly)) || 0,
      species_with_annotations: Number(parseField("species_with_annotations", raw.species_with_annotations)) || 0,
      sum_run_count: Number(parseField("sum_run_count", raw.sum_run_count)) || 0,
      sum_assembly_count: Number(parseField("sum_assembly_count", raw.sum_assembly_count)) || 0,
      sum_annotation_count: Number(parseField("sum_annotation_count", raw.sum_annotation_count)) || 0,
    }
    if (!node.taxid) continue
    parsed.push(node)
  }

  for (const node of pruneOrphanNodes(parsed)) {
    rowById.set(node.taxid, toTaxonRollupView(node))
  }

  for (const node of rowById.values()) {
    const pid = node.parent_taxid
    if (!pid || !rowById.has(pid)) continue
    if (!childrenByParent.has(pid)) childrenByParent.set(pid, [])
    childrenByParent.get(pid).push(node.taxid)
  }

  for (const [pid, ids] of childrenByParent) {
    ids.sort(
      (a, b) => (rowById.get(b)?.species_count_ncbi ?? 0) - (rowById.get(a)?.species_count_ncbi ?? 0),
    )
    childrenByParent.set(pid, ids)
  }

  return { rowById, childrenByParent }
}

export function getRowById(rowById, taxid) {
  return rowById.get(taxid)
}

export function getChildrenOf(childrenByParent, rowById, taxid) {
  const ids = childrenByParent.get(taxid) ?? []
  return ids.map((id) => rowById.get(id)).filter(Boolean)
}

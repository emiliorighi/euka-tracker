#!/usr/bin/env node
/**
 * Extract showcase JSON slices from rollup TSV (+ matrix genus for specimen stream).
 * Run: node scripts/extract-taxonomy-mock.mjs
 */
import { createReadStream, mkdirSync, writeFileSync } from "fs"
import { createInterface } from "readline"
import { dirname, join } from "path"
import { fileURLToPath } from "url"

const __dirname = dirname(fileURLToPath(import.meta.url))
const REPO = join(__dirname, "..", "..")
const ROLLUPS = join(REPO, "data", "staged", "06_taxon_rollups.tsv")
const MATRIX = join(REPO, "data", "staged", "05_eukaryotic_species_matrix.tsv")
const OUT_DIR = join(__dirname, "..", "lib", "taxonomy-mock", "data")

const EUKARYOTA = 2759
const METAZOA = 33208
const MAMMALIA = 40674
const THERIA = 32525

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
])

function enrichSlimRow(row) {
  row.species_count_matrix = row.species_count_with_data ?? 0
  row.species_with_annotation = row.species_with_annotations ?? 0
  return row
}

function parseRow(raw) {
  const row = {}
  for (const [k, v] of Object.entries(raw)) {
    if (NUMERIC_FIELDS.has(k)) {
      const n = v === "" ? 0 : Number(v)
      row[k] = Number.isFinite(n) ? n : 0
    } else {
      row[k] = v ?? ""
    }
  }
  return row
}

async function loadRollups() {
  const rowsById = new Map()
  const childrenByParent = new Map()

  const rl = createInterface({
    input: createReadStream(ROLLUPS),
    crlfDelay: Infinity,
  })

  let headers = null
  for await (const line of rl) {
    if (!headers) {
      headers = line.split("\t")
      continue
    }
    const parts = line.split("\t")
    const raw = Object.fromEntries(headers.map((h, i) => [h, parts[i] ?? ""]))
    const row = enrichSlimRow(parseRow(raw))
    rowsById.set(row.taxid, row)
    const pid = row.parent_taxid
    if (pid) {
      if (!childrenByParent.has(pid)) childrenByParent.set(pid, [])
      childrenByParent.get(pid).push(row.taxid)
    }
  }

  return { rowsById, childrenByParent }
}

function descendants(root, childrenByParent) {
  const seen = new Set()
  const stack = [root]
  while (stack.length) {
    const n = stack.pop()
    if (seen.has(n)) continue
    seen.add(n)
    for (const c of childrenByParent.get(n) ?? []) stack.push(c)
  }
  return seen
}

function ancestors(taxid, rowsById) {
  const chain = []
  let cur = taxid
  while (cur && rowsById.has(cur)) {
    chain.unshift(rowsById.get(cur))
    const pid = rowsById.get(cur).parent_taxid
    cur = pid || null
  }
  return chain
}

function childrenOf(parentId, childrenByParent, rowsById) {
  return (childrenByParent.get(parentId) ?? [])
    .map((id) => rowsById.get(id))
    .filter(Boolean)
    .sort((a, b) => b.species_count_matrix - a.species_count_matrix)
}

async function extractSpecimenSpecies(rowsById) {
  const rl = createInterface({
    input: createReadStream(MATRIX),
    crlfDelay: Infinity,
  })

  let headers = null
  const byGenus = new Map()

  for await (const line of rl) {
    if (!headers) {
      headers = line.split("\t")
      continue
    }
    const parts = line.split("\t")
    const raw = Object.fromEntries(headers.map((h, i) => [h, parts[i] ?? ""]))
    const lineage = (raw.tax_lineage || "").split(",").map((s) => parseInt(s.trim(), 10)).filter(Boolean)
    if (!lineage.length) continue

    let genusTaxid = null
    for (let i = lineage.length - 1; i >= 0; i--) {
      const tid = lineage[i]
      const node = rowsById.get(tid)
      if (node?.rank === "genus") {
        genusTaxid = tid
        break
      }
    }
    if (!genusTaxid) continue

    if (!byGenus.has(genusTaxid)) byGenus.set(genusTaxid, [])
    byGenus.get(genusTaxid).push({
      taxid: parseInt(raw.taxid, 10) || 0,
      scientific_name: raw.scientific_name || "",
      redlist_category: raw.redlist_category || "",
      assembly_count: parseInt(raw.assembly_count, 10) || 0,
      annotation_count: parseInt(raw.annotation_count, 10) || 0,
      wgs_long_count: parseInt(raw.wgs_long_count, 10) || 0,
      wgs_short_count: parseInt(raw.wgs_short_count, 10) || 0,
      rnaseq_long_count: parseInt(raw.rnaseq_long_count, 10) || 0,
      rnaseq_short_count: parseInt(raw.rnaseq_short_count, 10) || 0,
      ref_assembly_total_sequence_length: parseFloat(raw.ref_assembly_total_sequence_length) || 0,
      ref_assembly_gc_percent: parseFloat(raw.ref_assembly_gc_percent) || 0,
      ref_assembly_scaffold_n50: parseFloat(raw.ref_assembly_scaffold_n50) || 0,
      ref_assembly_level: raw.ref_assembly_level || "",
      ref_annotation_busco_complete: parseFloat(raw.ref_annotation_busco_complete) || 0,
      tax_lineage: raw.tax_lineage || "",
    })
  }

  let bestGenus = null
  let bestSpecies = []
  for (const [gid, species] of byGenus) {
    if (species.length >= 15 && species.length <= 40) {
      if (!bestGenus || species.length > bestSpecies.length) {
        bestGenus = gid
        bestSpecies = species
      }
    }
  }
  if (!bestGenus) {
    for (const [gid, species] of byGenus) {
      if (species.length >= 10 && (!bestGenus || species.length > bestSpecies.length)) {
        bestGenus = gid
        bestSpecies = species
      }
    }
  }

  const genusRow = rowsById.get(bestGenus)
  return {
    genus_taxid: bestGenus,
    genus_name: genusRow?.scientific_name ?? "Unknown genus",
    genus_rank: genusRow?.rank ?? "genus",
    species: bestSpecies.sort((a, b) => a.scientific_name.localeCompare(b.scientific_name)),
  }
}

const MAMMALIA_DEPTH_RANKS = new Set([
  "clade",
  "subclass",
  "infraclass",
  "superorder",
  "suborder",
  "order",
  "family",
])

function ancestorIds(taxid, rowsById) {
  const ids = []
  let cur = taxid
  while (cur && rowsById.has(cur)) {
    ids.unshift(cur)
    const pid = rowsById.get(cur).parent_taxid
    cur = pid || null
  }
  return ids
}

function sortedSiblings(parentId, childrenByParent, rowsById, limit) {
  return (childrenByParent.get(parentId) ?? [])
    .map((id) => rowsById.get(id))
    .filter(Boolean)
    .sort((a, b) => b.species_count_matrix - a.species_count_matrix)
    .slice(0, limit)
    .map((r) => r.taxid)
}

/** Induced atlas subtree for /taxonomy/atlas (~1.1k nodes). */
function buildAtlasSubtree(rowsById, childrenByParent, genusTaxid) {
  const included = new Set()

  for (const tid of ancestorIds(MAMMALIA, rowsById)) included.add(tid)
  if (genusTaxid) {
    for (const tid of ancestorIds(genusTaxid, rowsById)) included.add(tid)
  }

  for (const tid of childrenByParent.get(EUKARYOTA) ?? []) included.add(tid)

  if (genusTaxid) {
    for (const tid of ancestorIds(genusTaxid, rowsById)) {
      const row = rowsById.get(tid)
      if (!row?.parent_taxid) continue
      for (const sid of sortedSiblings(row.parent_taxid, childrenByParent, rowsById, 8)) {
        included.add(sid)
      }
    }
  }

  const mammaliaDesc = descendants(MAMMALIA, childrenByParent)
  for (const tid of mammaliaDesc) {
    const row = rowsById.get(tid)
    if (!row) continue
    if (tid === MAMMALIA || MAMMALIA_DEPTH_RANKS.has(row.rank)) included.add(tid)
  }

  for (const tid of [...included]) {
    const row = rowsById.get(tid)
    if (row?.rank !== "family") continue
    const genera = (childrenByParent.get(tid) ?? [])
      .map((id) => rowsById.get(id))
      .filter((r) => r?.rank === "genus")
      .sort((a, b) => b.species_count_matrix - a.species_count_matrix)
      .slice(0, 12)
    for (const g of genera) included.add(g.taxid)
  }

  const taxa = {}
  for (const tid of included) {
    const row = rowsById.get(tid)
    if (row) taxa[String(tid)] = row
  }

  const childrenIndex = {}
  let edgeCount = 0
  for (const tid of included) {
    const childIds = (childrenByParent.get(tid) ?? [])
      .filter((cid) => included.has(cid))
      .map((cid) => rowsById.get(cid))
      .filter(Boolean)
      .sort((a, b) => b.species_count_matrix - a.species_count_matrix)
      .map((r) => r.taxid)
    if (childIds.length) {
      childrenIndex[String(tid)] = childIds
      edgeCount += childIds.length
    }
  }

  return { taxa, childrenIndex, nodeCount: included.size, edgeCount }
}

function writeJson(name, data) {
  writeFileSync(join(OUT_DIR, name), JSON.stringify(data, null, 2) + "\n")
}

async function main() {
  mkdirSync(OUT_DIR, { recursive: true })
  const { rowsById, childrenByParent } = await loadRollups()

  const showcaseIds = [EUKARYOTA, METAZOA, MAMMALIA, THERIA, 33154, 33090, 32524]
  const taxa = {}
  for (const id of showcaseIds) {
    if (rowsById.has(id)) taxa[String(id)] = rowsById.get(id)
  }

  const mammaliaDesc = descendants(MAMMALIA, childrenByParent)
  const orders = [...mammaliaDesc]
    .map((id) => rowsById.get(id))
    .filter((r) => r?.rank === "order")
    .sort((a, b) => b.species_count_matrix - a.species_count_matrix)

  const specimen = await extractSpecimenSpecies(rowsById)
  if (specimen.genus_taxid && rowsById.has(specimen.genus_taxid)) {
    taxa[String(specimen.genus_taxid)] = rowsById.get(specimen.genus_taxid)
  }

  writeJson("taxa.json", taxa)
  writeJson("eukaryota-children.json", childrenOf(EUKARYOTA, childrenByParent, rowsById))
  writeJson("mammalia-ancestors.json", ancestors(MAMMALIA, rowsById))
  writeJson("mammalia-orders.json", orders)
  writeJson("mammalia-row.json", rowsById.get(MAMMALIA))
  writeJson("eukaryota-row.json", rowsById.get(EUKARYOTA))
  writeJson("metazoa-row.json", rowsById.get(METAZOA))
  writeJson("theria-children.json", childrenOf(THERIA, childrenByParent, rowsById))
  writeJson("mammalia-children.json", childrenOf(MAMMALIA, childrenByParent, rowsById))
  writeJson("opisthokonta-children.json", childrenOf(33154, childrenByParent, rowsById))
  writeJson("metazoa-children.json", childrenOf(METAZOA, childrenByParent, rowsById))
  writeJson("specimen-species.json", specimen)

  const atlas = buildAtlasSubtree(rowsById, childrenByParent, specimen.genus_taxid)
  writeJson("atlas-taxa.json", atlas.taxa)
  writeJson("atlas-children-index.json", atlas.childrenIndex)

  console.log("Wrote taxonomy mock data to", OUT_DIR)
  console.log("  eukaryota children:", childrenOf(EUKARYOTA, childrenByParent, rowsById).length)
  console.log("  mammalia orders:", orders.length)
  console.log("  theria children:", childrenOf(THERIA, childrenByParent, rowsById).length)
  console.log("  specimen genus:", specimen.genus_name, specimen.species.length, "species")
  console.log("  atlas subtree:", atlas.nodeCount, "nodes,", atlas.edgeCount, "edges")
}

main().catch((err) => {
  console.error(err)
  process.exit(1)
})

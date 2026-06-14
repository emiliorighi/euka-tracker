import type { SpecimenSpeciesRow, TaxonRollup } from "@/lib/taxonomy-mock/types"
import { formatDualCount, pctCatalog, pctCatalogLabel } from "@/lib/taxonomy-mock"

export function formatLitDual(row: TaxonRollup): string {
  return formatDualCount(row.species_count_matrix, row.species_count_ncbi)
}

export function formatLitPct(row: TaxonRollup): string {
  return pctCatalogLabel(row)
}

export function litPct(row: TaxonRollup): number {
  return pctCatalog(row)
}

export function isGhostRow(row: TaxonRollup): boolean {
  return row.species_count_matrix <= 0
}

export function stoneBrightness(row: SpecimenSpeciesRow): number {
  const hasReads =
    row.wgs_long_count + row.wgs_short_count + row.rnaseq_long_count + row.rnaseq_short_count > 0
  const hasAsm = row.assembly_count > 0
  const hasAnnot = row.annotation_count > 0
  const tiers = [hasReads, hasAsm, hasAnnot].filter(Boolean).length
  if (tiers === 0) return 0.22
  if (tiers === 1) return 0.42
  if (tiers === 2) return 0.68
  return 1
}

export function stoneTierFlags(row: SpecimenSpeciesRow) {
  return {
    reads:
      row.wgs_long_count + row.wgs_short_count + row.rnaseq_long_count + row.rnaseq_short_count > 0,
    asm: row.assembly_count > 0,
    annot: row.annotation_count > 0,
  }
}

export function cladeCardSnapshotHtml(row: TaxonRollup): string {
  const lit = litPct(row)
  const ghost = isGhostRow(row)
  const borderClass = ghost ? "border-dashed border-white/15 bg-white/[0.02]" : "border-white/10 bg-card/40"
  const crestOpacity = 0.3 + lit * 0.5
  const glow = ghost ? "" : `inset 0 0 ${12 + lit * 20}px oklch(0.72 0.16 152 / ${0.06 + lit * 0.12})`
  return `<div class="clade-card-shell clade-morph-snapshot relative overflow-hidden rounded-xl border p-3 pt-4 text-left ${borderClass}" style="box-shadow:${glow}"><div class="clade-card-crest pointer-events-none absolute inset-x-3 top-0 h-6 rounded-b-[100%] border-x border-b border-primary/25 bg-primary/5" style="opacity:${crestOpacity}"></div><div class="relative space-y-1"><p class="lit-scientific taxon-name line-clamp-2 text-xs leading-tight font-medium italic">${row.scientific_name}</p><span class="text-[10px] capitalize text-muted-foreground">${row.rank}</span><div class="space-y-1 pt-1"><div class="h-1 overflow-hidden rounded-full bg-secondary/80"><div class="clade-lit-bar h-full rounded-full bg-primary" style="width:${Math.round(lit * 100)}%"></div></div><p class="font-mono text-[9px] tabular-nums text-muted-foreground">${row.species_count_matrix.toLocaleString()} lit · ${(lit * 100).toFixed(1)}%</p></div></div></div>`
}

/** @deprecated use cladeCardSnapshotHtml */
export const portalSnapshotHtml = cladeCardSnapshotHtml

export type LevitationDetail = {
  taxid: number
  scientificName: string
  genusName: string
  redlist: string
  runCount: number
  assemblyCount: number
  annotationCount: number
  genomeSizeMb: number
  gcPercent: number
  scaffoldN50Mb: number
  busco: number
  assemblyLevel: string
}

export function specimenToLevitationDetail(
  row: SpecimenSpeciesRow,
  genusName: string,
): LevitationDetail {
  const runCount =
    row.wgs_long_count +
    row.wgs_short_count +
    row.rnaseq_long_count +
    row.rnaseq_short_count

  return {
    taxid: row.taxid,
    scientificName: row.scientific_name,
    genusName,
    redlist: row.redlist_category || "NE",
    runCount,
    assemblyCount: row.assembly_count,
    annotationCount: row.annotation_count,
    genomeSizeMb: row.ref_assembly_total_sequence_length / 1e6,
    gcPercent: row.ref_assembly_gc_percent,
    scaffoldN50Mb: row.ref_assembly_scaffold_n50 / 1e6,
    busco: row.ref_annotation_busco_complete,
    assemblyLevel: row.ref_assembly_level || "—",
  }
}

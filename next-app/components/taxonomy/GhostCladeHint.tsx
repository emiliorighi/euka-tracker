import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import { TaxonName } from "./TaxonName"
import { cn } from "@/lib/utils"

export function GhostCladeHint({ row }: { row: TaxonRollup }) {
  if (row.species_count_matrix > 0) return null
  return (
    <p className="text-sm text-muted-foreground">
      No catalog species yet — {row.species_count_ncbi.toLocaleString()} NCBI species in this clade.
    </p>
  )
}

export function GhostRingStyle({ ghost }: { ghost: boolean }) {
  return ghost
    ? { fill: "var(--ghost-clade)", stroke: "var(--ghost-border)" }
    : undefined
}

export function cladeIsGhost(row: TaxonRollup) {
  return row.species_count_matrix <= 0
}

export function ringFillOpacity(row: TaxonRollup) {
  if (row.species_count_matrix <= 0) return 0.06
  if (row.species_count_ncbi <= 0) return 0.2
  return 0.15 + (row.species_count_matrix / row.species_count_ncbi) * 0.85
}

export function RankPill({ rank, className }: { rank: string; className?: string }) {
  return (
    <span
      className={cn(
        "rounded-md bg-secondary px-2 py-0.5 text-xs capitalize text-muted-foreground",
        className,
      )}
    >
      {rank || "no rank"}
    </span>
  )
}

export function FocusHeader({ row }: { row: TaxonRollup }) {
  return (
    <div className="space-y-1">
      <div className="flex flex-wrap items-center gap-2">
        <TaxonName name={row.scientific_name} className="text-lg" />
        <RankPill rank={row.rank} />
      </div>
      <GhostCladeHint row={row} />
    </div>
  )
}

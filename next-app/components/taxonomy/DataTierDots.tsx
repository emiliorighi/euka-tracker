import type { SpecimenSpeciesRow } from "@/lib/taxonomy-mock/types"
import { cn } from "@/lib/utils"

export function DataTierDots({ row }: { row: SpecimenSpeciesRow }) {
  const hasReads =
    row.wgs_long_count + row.wgs_short_count + row.rnaseq_long_count + row.rnaseq_short_count > 0
  const hasAsm = row.assembly_count > 0
  const hasAnnot = row.annotation_count > 0
  return (
    <div className="flex gap-1" aria-hidden>
      <span className={cn("size-1.5 rounded-full", hasReads ? "bg-chart-2" : "bg-muted")} />
      <span className={cn("size-1.5 rounded-full", hasAsm ? "bg-primary" : "bg-muted")} />
      <span className={cn("size-1.5 rounded-full", hasAnnot ? "bg-chart-4" : "bg-muted")} />
    </div>
  )
}

export function speciesTileBrightness(row: SpecimenSpeciesRow): number {
  const hasReads =
    row.wgs_long_count + row.wgs_short_count + row.rnaseq_long_count + row.rnaseq_short_count > 0
  const hasAsm = row.assembly_count > 0
  const hasAnnot = row.annotation_count > 0
  const tiers = [hasReads, hasAsm, hasAnnot].filter(Boolean).length
  if (tiers === 0) return 0.25
  if (tiers === 1) return 0.45
  if (tiers === 2) return 0.7
  return 1
}

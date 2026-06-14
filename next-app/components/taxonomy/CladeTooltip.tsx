import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import { formatDualCount, pctCatalogLabel } from "@/lib/taxonomy-mock"
import { TaxonName } from "./TaxonName"
import { RankPill } from "./GhostCladeHint"
import { cn } from "@/lib/utils"

export function CladeTooltipCard({
  row,
  extra,
  className,
}: {
  row: TaxonRollup
  extra?: string
  className?: string
}) {
  return (
    <div
      className={cn(
        "rounded-lg border border-border bg-card/95 px-3 py-2 text-left shadow-lg backdrop-blur-sm",
        className,
      )}
    >
      <TaxonName name={row.scientific_name} className="text-sm" />
      <RankPill rank={row.rank} className="mt-1" />
      <p className="mt-1 font-mono text-xs tabular-nums">{formatDualCount(row.species_count_matrix, row.species_count_ncbi)}</p>
      <p className="text-xs text-muted-foreground">{pctCatalogLabel(row)} catalog coverage</p>
      {extra && <p className="mt-1 text-xs text-muted-foreground">{extra}</p>}
    </div>
  )
}

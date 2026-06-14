import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import { LitScientificName } from "./LitScientificName"
import { formatLitDual } from "./lit-room-utils"

export function ChamberHeadline({ row }: { row: TaxonRollup }) {
  return (
    <header className="chamber-headline space-y-2">
      <div className="flex flex-wrap items-baseline gap-x-3 gap-y-1">
        <LitScientificName name={row.scientific_name} className="text-lg md:text-xl" />
        <span className="rounded-full border border-primary/25 bg-primary/10 px-2 py-0.5 text-[10px] uppercase tracking-wider text-primary">
          {row.rank || "clade"}
        </span>
      </div>
      <p className="font-mono text-xs tabular-nums text-muted-foreground">{formatLitDual(row)}</p>
    </header>
  )
}

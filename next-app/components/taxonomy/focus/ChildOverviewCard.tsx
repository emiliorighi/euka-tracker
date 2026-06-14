"use client"

import { forwardRef } from "react"
import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import { pctCatalog, pctCatalogLabel } from "@/lib/taxonomy-mock"
import { cladeIsGhost } from "../GhostCladeHint"
import { TaxonName } from "../TaxonName"
import { cn } from "@/lib/utils"

export function cardSnapshotHtml(row: TaxonRollup): string {
  return `<div class="p-2"><p class="text-sm font-medium">${row.scientific_name}</p><p class="text-xs capitalize text-muted-foreground">${row.rank}</p></div>`
}

export const ChildOverviewCard = forwardRef<
  HTMLButtonElement,
  {
    row: TaxonRollup
    compact?: boolean
    selected?: boolean
    onSelect: () => void
    onClick?: (e: React.MouseEvent<HTMLButtonElement>) => void
    className?: string
  }
>(function ChildOverviewCard(
  { row, compact, selected, onSelect, onClick, className },
  ref,
) {
  const ghost = cladeIsGhost(row)
  const lit = pctCatalog(row)
  const height = compact
    ? undefined
    : 72 + Math.min(48, Math.log1p(row.species_count_ncbi) * 8)

  return (
    <button
      ref={ref}
      type="button"
      data-focus-card={row.taxid}
      onClick={(e) => {
        onSelect()
        onClick?.(e)
      }}
      disabled={false}
      className={cn(
        "child-card flex flex-col rounded-lg border text-left transition-shadow",
        compact ? "w-full p-2" : "w-28 shrink-0 p-2",
        ghost ? "border-dashed border-border/60 bg-card/30" : "border-border bg-card/80",
        selected && "ring-2 ring-primary ring-offset-1 ring-offset-background",
        "hover:border-primary/40 hover:shadow-md",
        className,
      )}
      data-selected={selected ? "true" : undefined}
      style={height != null ? { minHeight: height } : undefined}
      title={`${row.scientific_name} — ${pctCatalogLabel(row)} lit`}
    >
      <TaxonName
        name={row.scientific_name}
        className={cn("line-clamp-2 leading-tight", compact ? "text-xs" : "text-xs")}
      />
      <span className="mt-0.5 text-[10px] capitalize text-muted-foreground">{row.rank}</span>
      <div className={cn("pt-1.5", compact ? "" : "mt-auto pt-2")}>
        <div className="h-1 overflow-hidden rounded-full bg-secondary">
          <div
            className="h-full rounded-full bg-primary transition-all"
            style={{ width: `${Math.round(lit * 100)}%` }}
          />
        </div>
        <p className="mt-0.5 font-mono text-[9px] tabular-nums text-muted-foreground">
          {row.species_count_matrix.toLocaleString()} lit
        </p>
      </div>
    </button>
  )
})

"use client"

import { forwardRef } from "react"
import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import { CladeCardShell } from "./CladeCardShell"
import { formatLitPct } from "./lit-room-utils"
import { cn } from "@/lib/utils"

export const ThresholdCard = forwardRef<
  HTMLButtonElement,
  {
    row: TaxonRollup
    selected?: boolean
    isMorphSource?: boolean
    onSelect: () => void
    onClick?: (e: React.MouseEvent<HTMLButtonElement>) => void
    className?: string
  }
>(function ThresholdCard({ row, selected, isMorphSource, onSelect, onClick, className }, ref) {
  return (
    <button
      ref={ref}
      type="button"
      data-doorway={row.taxid}
      onClick={(e) => {
        onSelect()
        onClick?.(e)
      }}
      className={cn(
        "threshold-card doorway-card group shrink-0 snap-center text-left transition-transform duration-300 hover:-translate-y-1",
        "w-[9.5rem] sm:w-[10rem]",
        selected && "ring-2 ring-primary/70 ring-offset-2 ring-offset-background rounded-xl",
        className,
      )}
      data-selected={selected ? "true" : undefined}
      title={`${row.scientific_name} — ${formatLitPct(row)} lit`}
    >
      <CladeCardShell
        row={row}
        variant="compact"
        className={cn("h-full hover:border-primary/40", isMorphSource && "is-morph-source")}
      />
    </button>
  )
})

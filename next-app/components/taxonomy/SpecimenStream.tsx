"use client"

import { useRef } from "react"
import type { SpecimenSpeciesRow } from "@/lib/taxonomy-mock/types"
import { TaxonName } from "./TaxonName"
import { cn } from "@/lib/utils"
import { Pin, PinOff } from "lucide-react"

function DataTierDots({ row }: { row: SpecimenSpeciesRow }) {
  const hasReads =
    row.wgs_long_count + row.wgs_short_count + row.rnaseq_long_count + row.rnaseq_short_count > 0
  const hasAsm = row.assembly_count > 0
  const hasAnnot = row.annotation_count > 0
  const tiers = [
    { on: hasReads, label: "reads", color: "bg-chart-2" },
    { on: hasAsm, label: "assembly", color: "bg-primary" },
    { on: hasAnnot, label: "annotation", color: "bg-chart-4" },
  ]
  return (
    <div className="flex gap-1" title="reads · assembly · annotation">
      {tiers.map((t) => (
        <span
          key={t.label}
          className={cn("size-2 rounded-full", t.on ? t.color : "bg-muted")}
        />
      ))}
    </div>
  )
}

export function SpecimenStream({
  genusName,
  species,
  focusedIndex,
  pinnedTaxid,
  onSelect,
  onPin,
  className,
}: {
  genusName: string
  species: SpecimenSpeciesRow[]
  focusedIndex?: number
  pinnedTaxid?: number | null
  onSelect: (row: SpecimenSpeciesRow) => void
  onPin?: (row: SpecimenSpeciesRow | null) => void
  className?: string
}) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const pinned = pinnedTaxid != null ? species.find((s) => s.taxid === pinnedTaxid) : null

  return (
    <div className={cn("min-w-0 space-y-3", className)}>
      {pinned && (
        <div className="flex items-center gap-3 rounded-lg border border-primary/30 bg-primary/5 p-3">
          <div className="flex size-10 items-center justify-center rounded-lg bg-secondary text-lg">
            {pinned.scientific_name.charAt(0)}
          </div>
          <div className="min-w-0 flex-1">
            <TaxonName name={pinned.scientific_name} className="text-sm" />
            <DataTierDots row={pinned} />
          </div>
          <button
            type="button"
            onClick={() => onPin?.(null)}
            className="text-muted-foreground hover:text-foreground"
            aria-label="Unpin"
          >
            <PinOff className="size-4" />
          </button>
        </div>
      )}
      <p className="text-sm text-muted-foreground">
        Genus <TaxonName name={genusName} /> — {species.length} catalog species
      </p>
      <div
        ref={scrollRef}
        className="flex min-w-0 gap-3 overflow-x-auto overscroll-x-contain pb-4 snap-x snap-mandatory"
      >
        {species.map((row, i) => {
          const focused = focusedIndex === i
          const isPinned = pinnedTaxid === row.taxid
          return (
            <div
              key={row.taxid}
              className={cn(
                "relative shrink-0 snap-start",
                focused && "ring-2 ring-primary ring-offset-2 ring-offset-background rounded-xl",
              )}
            >
              <button
                type="button"
                onClick={() => onSelect(row)}
                className="w-44 rounded-xl border border-border bg-card p-3 text-left transition-colors hover:border-primary/40 hover:bg-secondary/50"
              >
                <div className="mb-3 flex h-20 items-center justify-center rounded-lg bg-secondary/80 text-2xl text-muted-foreground/40">
                  {row.scientific_name.charAt(0)}
                </div>
                <TaxonName name={row.scientific_name} className="block text-sm leading-tight" />
                <div className="mt-2 flex items-center justify-between">
                  <DataTierDots row={row} />
                  {row.redlist_category && (
                    <span className="text-[10px] text-muted-foreground">{row.redlist_category}</span>
                  )}
                </div>
              </button>
              {onPin && (
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation()
                    onPin(isPinned ? null : row)
                  }}
                  className={cn(
                    "absolute right-2 top-2 rounded-md p-1",
                    isPinned ? "text-primary" : "text-muted-foreground hover:text-foreground",
                  )}
                  aria-label={isPinned ? "Unpin" : "Pin specimen"}
                >
                  <Pin className="size-3.5" />
                </button>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}

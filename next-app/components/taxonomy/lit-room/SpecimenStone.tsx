"use client"

import { forwardRef } from "react"
import type { SpecimenSpeciesRow } from "@/lib/taxonomy-mock/types"
import { LitScientificName } from "./LitScientificName"
import { SpecimenGlyphs } from "./SpecimenGlyphs"
import { stoneBrightness } from "./lit-room-utils"
import { cn } from "@/lib/utils"

export const SpecimenStone = forwardRef<
  HTMLButtonElement,
  {
    row: SpecimenSpeciesRow
    selected?: boolean
    onSelect: () => void
    onClick?: (e: React.MouseEvent<HTMLButtonElement>) => void
    className?: string
  }
>(function SpecimenStone({ row, selected, onSelect, onClick, className }, ref) {
  const brightness = stoneBrightness(row)
  const hasRedlist = Boolean(row.redlist_category && row.redlist_category !== "NE")

  return (
    <button
      ref={ref}
      type="button"
      data-species-tile={row.taxid}
      onClick={(e) => {
        onSelect()
        onClick?.(e)
      }}
      className={cn(
        "specimen-stone species-tile group relative aspect-square overflow-hidden rounded-lg border text-left transition-all duration-300",
        brightness < 0.5 ? "border-white/10 bg-white/[0.03]" : "border-primary/20 bg-card/50",
        selected && "ring-2 ring-primary/70 ring-offset-2 ring-offset-background",
        "hover:-translate-y-0.5 hover:border-primary/40 hover:shadow-[0_8px_24px_oklch(0.72_0.16_152/0.12)]",
        className,
      )}
      data-selected={selected ? "true" : undefined}
      title={row.scientific_name}
    >
      <div
        className="specimen-stone-glow pointer-events-none absolute inset-0 opacity-80 transition-opacity duration-500 group-hover:opacity-100"
        style={{
          background: `radial-gradient(circle at 50% 80%, oklch(0.72 0.16 152 / ${brightness * 0.35}) 0%, transparent 70%)`,
        }}
        aria-hidden
      />
      <div className="specimen-stone-grain pointer-events-none absolute inset-0 opacity-30" aria-hidden />
      {hasRedlist && (
        <span
          className="absolute right-1.5 top-1.5 size-2 rounded-full bg-amber-400 shadow-[0_0_8px_oklch(0.78_0.15_75/0.8)]"
          aria-label="IUCN assessed"
        />
      )}
      <div className="relative flex h-full flex-col justify-between p-2">
        <LitScientificName name={row.scientific_name} className="line-clamp-3 text-[10px] leading-tight" />
        <SpecimenGlyphs row={row} />
      </div>
    </button>
  )
})

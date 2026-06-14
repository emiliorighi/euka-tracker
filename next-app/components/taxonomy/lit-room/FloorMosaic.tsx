"use client"

import { useEffect, useRef } from "react"
import type { SpecimenSpeciesRow } from "@/lib/taxonomy-mock/types"
import { SpecimenStone } from "./SpecimenStone"
import { cn } from "@/lib/utils"

export function FloorMosaic({
  species,
  genusName,
  selectedIndex,
  onSelectIndex,
  onLevitate,
  isBusy,
  className,
}: {
  species: SpecimenSpeciesRow[]
  genusName?: string
  selectedIndex: number
  onSelectIndex: (index: number) => void
  onLevitate: (row: SpecimenSpeciesRow, sourceEl: HTMLButtonElement | null) => void
  isBusy?: boolean
  className?: string
}) {
  const gridRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const stone = gridRef.current?.querySelector(`[data-species-tile][data-selected="true"]`)
    stone?.scrollIntoView({ block: "nearest", behavior: "smooth" })
  }, [selectedIndex])

  if (species.length === 0) return null

  return (
    <div className={cn("floor-mosaic min-w-0 space-y-2", className)}>
      <h3 className="text-sm font-medium tracking-wide" id="lit-room-floor-heading">
        Floor mosaic{" "}
        <span className="font-normal text-muted-foreground">
          ({species.length}
          {genusName ? ` · ${genusName}` : ""})
        </span>
      </h3>
      <div className="floor-mosaic-perspective rounded-xl border border-white/5 bg-black/10 p-2">
        <div
          ref={gridRef}
          className="species-tile-grid floor-mosaic-grid grid grid-cols-2 gap-2 sm:grid-cols-3 lg:grid-cols-4"
          aria-labelledby="lit-room-floor-heading"
        >
          {species.map((row, i) => (
            <SpecimenStone
              key={row.taxid}
              row={row}
              selected={selectedIndex === i}
              onSelect={() => onSelectIndex(i)}
              onClick={(e) => {
                if (isBusy) return
                onLevitate(row, e.currentTarget)
              }}
            />
          ))}
        </div>
      </div>
    </div>
  )
}

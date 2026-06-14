"use client"

import { useState } from "react"
import type { SpecimenSpeciesRow } from "@/lib/taxonomy-mock/types"
import { getSpecimenSlice } from "@/lib/taxonomy-mock"
import { specimenToSpecies } from "@/lib/taxonomy-mock/species-adapter"
import type { Species } from "@/lib/biodiversity-data"
import { DataTierDots } from "../DataTierDots"
import { TaxonName } from "../TaxonName"
import { SpeciesDetailSheet } from "@/components/species-detail-sheet"
import { cn } from "@/lib/utils"

export function FocusSpeciesList({
  species,
  genusName,
  className,
}: {
  species: SpecimenSpeciesRow[]
  genusName?: string
  className?: string
}) {
  const slice = getSpecimenSlice()
  const genus = genusName ?? slice.genus_name
  const [selected, setSelected] = useState<Species | null>(null)
  const [open, setOpen] = useState(false)

  if (species.length === 0) {
    return (
      <p className={cn("text-sm text-muted-foreground", className)}>
        Species list appears at genus rank in the catalog (demo: jump to Trichosanthes).
      </p>
    )
  }

  return (
    <>
      <section className={cn("min-w-0 space-y-2", className)} aria-label="Species in clade">
        <h3 className="text-sm font-medium" id="focus-species-heading">
          Catalog species{" "}
          <span className="font-normal text-muted-foreground">({species.length})</span>
        </h3>
        <ul
          className="max-h-56 min-w-0 space-y-1 overflow-y-auto rounded-lg border border-border/60 p-1"
          aria-labelledby="focus-species-heading"
        >
          {species.map((row) => (
            <li key={row.taxid}>
              <button
                type="button"
                onClick={() => {
                  setSelected(specimenToSpecies(row, genus))
                  setOpen(true)
                }}
                className="flex w-full items-center justify-between gap-2 rounded-md px-2 py-1.5 text-left hover:bg-secondary/60"
              >
                <TaxonName name={row.scientific_name} className="min-w-0 truncate text-sm" />
                <DataTierDots row={row} />
              </button>
            </li>
          ))}
        </ul>
      </section>
      <SpeciesDetailSheet species={selected} open={open} onOpenChange={setOpen} />
    </>
  )
}

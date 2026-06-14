"use client"

import { useState } from "react"
import type { SpecimenSpeciesRow } from "@/lib/taxonomy-mock/types"
import { getSpecimenGenusTaxid, getSpecimenSlice } from "@/lib/taxonomy-mock"
import { specimenToSpecies } from "@/lib/taxonomy-mock/species-adapter"
import type { IucnStatus } from "@/lib/biodiversity-data"
import { DataTierDots } from "@/components/taxonomy/DataTierDots"
import { TaxonName } from "@/components/taxonomy/TaxonName"
import { SpeciesDetailSheet } from "@/components/species-detail-sheet"
import { IucnBadge } from "@/components/iucn-badge"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

const REDLIST_TO_IUCN: Record<string, IucnStatus> = {
  EX: "EX",
  EW: "EW",
  CR: "CR",
  EN: "EN",
  VU: "VU",
  NT: "NT",
  LC: "LC",
  DD: "DD",
  NE: "DD",
}

function formatGenomeMb(bytes: number): string {
  const mb = bytes / 1e6
  if (mb <= 0) return "—"
  if (mb >= 1000) return `${(mb / 1000).toFixed(1)} Gb`
  return `${mb.toFixed(0)} Mb`
}

export function AtlasSpeciesGrid({
  species,
  genusName,
  onJumpToGenus,
  className,
}: {
  species: SpecimenSpeciesRow[]
  genusName: string
  onJumpToGenus: () => void
  className?: string
}) {
  const slice = getSpecimenSlice()
  const genusTaxid = getSpecimenGenusTaxid()
  const [selected, setSelected] = useState<ReturnType<typeof specimenToSpecies> | null>(null)
  const [open, setOpen] = useState(false)

  return (
    <section className={cn("atlas-species min-w-0 space-y-4", className)} aria-label="Related species">
      <div>
        <h3 className="text-base font-medium">Related species</h3>
        <p className="text-xs text-muted-foreground">
          {species.length > 0
            ? `${species.length} catalog records under this clade`
            : `Species list available at genus rank (demo: ${slice.genus_name})`}
        </p>
      </div>

      {species.length === 0 ? (
        <div className="rounded-xl border border-dashed border-border/60 bg-card/30 px-4 py-8 text-center">
          <p className="text-sm text-muted-foreground">
            No species records at this rank in the catalog slice.
          </p>
          <Button variant="secondary" size="sm" className="mt-3" onClick={onJumpToGenus}>
            Jump to {slice.genus_name}
          </Button>
          <p className="mt-2 font-mono text-[10px] text-muted-foreground">taxid {genusTaxid}</p>
        </div>
      ) : (
        <ul className="grid gap-3 sm:grid-cols-2 xl:grid-cols-3">
          {species.map((row) => {
            const iucnKey = (row.redlist_category || "DD").toUpperCase()
            const iucn = REDLIST_TO_IUCN[iucnKey] ?? "DD"
            return (
              <li key={row.taxid}>
                <button
                  type="button"
                  data-atlas-species={row.taxid}
                  onClick={() => {
                    setSelected(specimenToSpecies(row, genusName))
                    setOpen(true)
                  }}
                  className="atlas-species-card flex w-full flex-col rounded-xl border border-border/60 bg-card/40 p-3 text-left"
                >
                  <div className="flex items-start justify-between gap-2">
                    <TaxonName name={row.scientific_name} className="text-sm leading-tight" />
                    <IucnBadge status={iucn} />
                  </div>
                  <div className="mt-3 flex items-center justify-between">
                    <DataTierDots row={row} />
                    <span className="font-mono text-[10px] tabular-nums text-muted-foreground">
                      {formatGenomeMb(row.ref_assembly_total_sequence_length)}
                    </span>
                  </div>
                  <p className="mt-2 text-[10px] text-muted-foreground">
                    BUSCO {row.ref_annotation_busco_complete.toFixed(0)}% · {row.ref_assembly_level || "—"}
                  </p>
                </button>
              </li>
            )
          })}
        </ul>
      )}

      <SpeciesDetailSheet species={selected} open={open} onOpenChange={setOpen} />
    </section>
  )
}

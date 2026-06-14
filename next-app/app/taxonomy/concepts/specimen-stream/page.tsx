"use client"

import Link from "next/link"
import { useCallback, useState } from "react"
import { getSpecimenSlice, getTaxon } from "@/lib/taxonomy-mock"
import { specimenToSpecies } from "@/lib/taxonomy-mock/species-adapter"
import type { SpecimenSpeciesRow } from "@/lib/taxonomy-mock/types"
import { ConceptShell } from "@/components/taxonomy/ConceptShell"
import { SpecimenStream } from "@/components/taxonomy/SpecimenStream"
import { SpeciesDetailSheet } from "@/components/species-detail-sheet"
import { Button } from "@/components/ui/button"
import type { Species } from "@/lib/biodiversity-data"
import { useConceptKeyboard } from "@/hooks/useConceptKeyboard"

export default function SpecimenStreamConceptPage() {
  const slice = getSpecimenSlice()
  const genusRow = getTaxon(slice.genus_taxid)
  const [focusedIndex, setFocusedIndex] = useState(0)
  const [pinnedTaxid, setPinnedTaxid] = useState<number | null>(null)
  const [selected, setSelected] = useState<Species | null>(null)
  const [open, setOpen] = useState(false)

  const onSelect = useCallback(
    (row: SpecimenSpeciesRow) => {
      setSelected(specimenToSpecies(row, slice.genus_name))
      setOpen(true)
    },
    [slice.genus_name],
  )

  useConceptKeyboard({
    onArrowLeft: () => setFocusedIndex((i) => Math.max(0, i - 1)),
    onArrowRight: () => setFocusedIndex((i) => Math.min(slice.species.length - 1, i + 1)),
    onEnter: () => {
      const row = slice.species[focusedIndex]
      if (row) onSelect(row)
    },
  })

  return (
    <>
      <ConceptShell
        title="Specimen Stream"
        description="Horizontal scroll-snap species cards from a real genus slice in the species matrix. Use arrow keys; pin a card; click for detail."
        focusRow={genusRow}
        currentPath="/taxonomy/concepts/specimen-stream"
        headerExtra={
          <Button variant="outline" size="sm" asChild>
            <Link href="/taxonomy/atlas?view=scatter">Open in Atlas scatter</Link>
          </Button>
        }
      >
        <div className="min-w-0 overflow-hidden">
          <SpecimenStream
            genusName={slice.genus_name}
            species={slice.species}
            focusedIndex={focusedIndex}
            pinnedTaxid={pinnedTaxid}
            onSelect={onSelect}
            onPin={(row) => setPinnedTaxid(row?.taxid ?? null)}
          />
        </div>
      </ConceptShell>
      <SpeciesDetailSheet species={selected} open={open} onOpenChange={setOpen} />
    </>
  )
}

"use client"

import { useCallback, useMemo, useState } from "react"
import {
  EUKARYOTA_TAXID,
  getAncestorsOf,
  getChildrenOf,
  getEukaryotaRow,
  getRowById,
} from "@/lib/taxonomy-mock"
import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import { ConceptShell } from "@/components/taxonomy/ConceptShell"
import { ConceptStage } from "@/components/taxonomy/ConceptStage"
import { DescentHorizon } from "@/components/taxonomy/DescentHorizon"
import { DiveComputer } from "@/components/taxonomy/DiveComputer"
import { AncestorRail } from "@/components/taxonomy/AncestorRail"
import { GhostCladeHint } from "@/components/taxonomy/GhostCladeHint"
import { Button } from "@/components/ui/button"
import { useConceptKeyboard } from "@/hooks/useConceptKeyboard"

export default function DescentConceptPage() {
  const [focusTaxid, setFocusTaxid] = useState(EUKARYOTA_TAXID)
  const [selectedIndex, setSelectedIndex] = useState(0)

  const focus = useMemo(() => getRowById(focusTaxid) ?? getEukaryotaRow(), [focusTaxid])
  const children = useMemo(() => getChildrenOf(focusTaxid), [focusTaxid])
  const ancestors = useMemo(() => getAncestorsOf(focusTaxid), [focusTaxid])

  const selectedTaxid = children[selectedIndex]?.taxid

  const onSelect = useCallback((row: TaxonRollup) => {
    setFocusTaxid(row.taxid)
    setSelectedIndex(0)
  }, [])

  const ascend = useCallback(() => {
    if (focus.parent_taxid) {
      setFocusTaxid(focus.parent_taxid)
      setSelectedIndex(0)
    }
  }, [focus.parent_taxid])

  useConceptKeyboard({
    onEscape: ascend,
    onArrowUp: () => setSelectedIndex((i) => Math.max(0, i - 1)),
    onArrowDown: () => setSelectedIndex((i) => Math.min(children.length - 1, i + 1)),
    onEnter: () => {
      const row = children[selectedIndex]
      if (row) onSelect(row)
    },
    enabled: children.length > 0,
  })

  const depthHue = 160 + focus.depth_from_eukaryota * 2

  return (
    <ConceptShell
      title="The Descent"
      description="Horizon rings at each taxonomic level. Outer ring = NCBI species; inner glow = catalog coverage. Click a sector to drill down."
      focusRow={focus}
      currentPath="/taxonomy/concepts/descent"
      headerExtra={
        focusTaxid !== EUKARYOTA_TAXID ? (
          <Button variant="outline" size="sm" onClick={ascend}>
            Ascend (Esc)
          </Button>
        ) : null
      }
    >
      <ConceptStage
        depthHue={depthHue}
        rail={
          <AncestorRail
            ancestors={ancestors}
            focusTaxid={focusTaxid}
            onSelect={(id) => {
              setFocusTaxid(id)
              setSelectedIndex(0)
            }}
          />
        }
        viz={
          children.length > 0 ? (
            <DescentHorizon
              focus={focus}
              children={children}
              selectedTaxid={selectedTaxid}
              focusKey={focusTaxid}
              onSelect={onSelect}
            />
          ) : (
            <div className="space-y-2 text-center">
              <GhostCladeHint row={focus} />
              <p className="text-sm text-muted-foreground">No children in mock slice for this taxon.</p>
            </div>
          )
        }
        panel={<DiveComputer row={focus} />}
      />
    </ConceptShell>
  )
}

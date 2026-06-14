"use client"

import { useCallback, useMemo, useState } from "react"
import {
  EUKARYOTA_TAXID,
  getAncestorsOf,
  getChildrenOf,
  getEukaryotaChildren,
  getEukaryotaRow,
  getRowById,
} from "@/lib/taxonomy-mock"
import type { TaxonomyLens } from "@/lib/taxonomy-mock/types"
import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import { ConceptShell } from "@/components/taxonomy/ConceptShell"
import { ConceptStage } from "@/components/taxonomy/ConceptStage"
import { BiolumeField } from "@/components/taxonomy/BiolumeField"
import { DiveComputer } from "@/components/taxonomy/DiveComputer"
import { AncestorRail } from "@/components/taxonomy/AncestorRail"
import { CladeTooltipCard } from "@/components/taxonomy/CladeTooltip"
import { useConceptKeyboard } from "@/hooks/useConceptKeyboard"

export default function BiolumeConceptPage() {
  const [lens, setLens] = useState<TaxonomyLens>("catalog")
  const [focusTaxid, setFocusTaxid] = useState(EUKARYOTA_TAXID)
  const [selectedIndex, setSelectedIndex] = useState(0)

  const focus = useMemo(() => getRowById(focusTaxid) ?? getEukaryotaRow(), [focusTaxid])
  const cells = useMemo(() => {
    const ch = getChildrenOf(focusTaxid)
    return ch.length > 0 ? ch : getEukaryotaChildren()
  }, [focusTaxid])
  const ancestors = useMemo(() => getAncestorsOf(focusTaxid), [focusTaxid])
  const selectedRow = cells[selectedIndex] ?? null

  const onSelect = useCallback((row: TaxonRollup) => {
    const idx = cells.findIndex((c) => c.taxid === row.taxid)
    if (idx >= 0) setSelectedIndex(idx)
    if (getChildrenOf(row.taxid).length > 0) {
      setFocusTaxid(row.taxid)
      setSelectedIndex(0)
    }
  }, [cells])

  useConceptKeyboard({
    onArrowUp: () => setSelectedIndex((i) => Math.max(0, i - 1)),
    onArrowDown: () => setSelectedIndex((i) => Math.min(cells.length - 1, i + 1)),
    onEnter: () => {
      const row = cells[selectedIndex]
      if (row) onSelect(row)
    },
    enabled: cells.length > 0,
  })

  return (
    <ConceptShell
      title="Biolume Map"
      description="Kingdom-level cells under Eukaryota. Area scales with NCBI diversity; fill opacity reflects catalog coverage."
      focusRow={focus}
      currentPath="/taxonomy/concepts/biolume"
      lens={lens}
      onLensChange={setLens}
    >
      <ConceptStage
        depthHue={160 + focus.depth_from_eukaryota * 2}
        rail={
          <AncestorRail
            ancestors={ancestors}
            focusTaxid={focusTaxid}
            spillTaxid={selectedRow?.taxid}
            onSelect={setFocusTaxid}
          />
        }
        viz={
          <BiolumeField
            focus={focus}
            cells={cells}
            lens={lens}
            selectedTaxid={selectedRow?.taxid}
            onSelect={onSelect}
          />
        }
        panel={
          <div className="space-y-3">
            <DiveComputer row={focus} />
            {selectedRow && selectedRow.taxid !== focus.taxid && (
              <CladeTooltipCard row={selectedRow} extra="Selected cell" />
            )}
          </div>
        }
      />
    </ConceptShell>
  )
}

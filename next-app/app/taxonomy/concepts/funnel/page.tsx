"use client"

import { useState } from "react"
import {
  getEukaryotaRow,
  getMammaliaRow,
  getMetazoaRow,
} from "@/lib/taxonomy-mock"
import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import { ConceptShell } from "@/components/taxonomy/ConceptShell"
import { ConceptStage } from "@/components/taxonomy/ConceptStage"
import { FunnelCathedral } from "@/components/taxonomy/FunnelCathedral"
import { DiveComputer } from "@/components/taxonomy/DiveComputer"
import { FocusHeader } from "@/components/taxonomy/GhostCladeHint"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

const OPTIONS: { id: string; label: string; row: () => TaxonRollup }[] = [
  { id: "40674", label: "Mammalia", row: getMammaliaRow },
  { id: "2759", label: "Eukaryota", row: getEukaryotaRow },
  { id: "33208", label: "Metazoa", row: getMetazoaRow },
]

export default function FunnelConceptPage() {
  const [taxid, setTaxid] = useState("40674")
  const row = OPTIONS.find((o) => o.id === taxid)?.row() ?? getMammaliaRow()

  return (
    <ConceptShell
      title="Funnel Cathedral"
      description="Vertical stained-glass bands — genomic data funnel and conservation column. Click a band for stage details."
      focusRow={row}
      currentPath="/taxonomy/concepts/funnel"
      headerExtra={
        <Select value={taxid} onValueChange={setTaxid}>
          <SelectTrigger className="h-8 w-[140px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {OPTIONS.map((o) => (
              <SelectItem key={o.id} value={o.id}>
                {o.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      }
    >
      <ConceptStage
        viz={
          <div className="flex min-w-0 flex-col items-center gap-4">
            <FocusHeader row={row} />
            <FunnelCathedral row={row} />
          </div>
        }
        panel={<DiveComputer row={row} />}
      />
    </ConceptShell>
  )
}

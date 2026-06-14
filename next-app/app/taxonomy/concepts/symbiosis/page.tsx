"use client"

import { useMemo, useState } from "react"
import {
  getAllShowcaseTaxa,
  getMammaliaRow,
  getMetazoaRow,
  getSharedAncestor,
  getTaxon,
} from "@/lib/taxonomy-mock"
import { MAMMALIA_TAXID, METAZOA_TAXID } from "@/lib/taxonomy-mock/types"
import { ConceptShell } from "@/components/taxonomy/ConceptShell"
import { ConceptStage } from "@/components/taxonomy/ConceptStage"
import { SymbiosisCompare } from "@/components/taxonomy/SymbiosisCompare"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"

export default function SymbiosisConceptPage() {
  const [leftId, setLeftId] = useState(String(MAMMALIA_TAXID))
  const [rightId, setRightId] = useState(String(METAZOA_TAXID))

  const taxa = getAllShowcaseTaxa()
  const left = getTaxon(Number(leftId)) ?? getMammaliaRow()
  const right = getTaxon(Number(rightId)) ?? getMetazoaRow()
  const shared = useMemo(
    () => getSharedAncestor(left.taxid, right.taxid),
    [left.taxid, right.taxid],
  )

  return (
    <ConceptShell
      title="Compare as Symbiosis"
      description="Pin two clades — dual horizon rings, funnel diff, and rank node counter table from rollup columns."
      currentPath="/taxonomy/concepts/symbiosis"
      headerExtra={
        <div className="flex flex-wrap gap-2">
          <Select value={leftId} onValueChange={setLeftId}>
            <SelectTrigger className="h-8 w-[130px]">
              <SelectValue placeholder="Left" />
            </SelectTrigger>
            <SelectContent>
              {taxa.map((t) => (
                <SelectItem key={t.taxid} value={String(t.taxid)}>
                  {t.scientific_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Select value={rightId} onValueChange={setRightId}>
            <SelectTrigger className="h-8 w-[130px]">
              <SelectValue placeholder="Right" />
            </SelectTrigger>
            <SelectContent>
              {taxa.map((t) => (
                <SelectItem key={t.taxid} value={String(t.taxid)}>
                  {t.scientific_name}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </div>
      }
    >
      <ConceptStage
        viz={<SymbiosisCompare left={left} right={right} sharedAncestor={shared} />}
      />
    </ConceptShell>
  )
}

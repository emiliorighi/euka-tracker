"use client"

import { useMemo, useState } from "react"
import {
  getMammaliaAncestors,
  getMammaliaRow,
  getOrdersUnderMammalia,
} from "@/lib/taxonomy-mock"
import type { TaxonomyLens } from "@/lib/taxonomy-mock/types"
import { rankNodeCounts } from "@/lib/taxonomy/ranks"
import { ConceptShell } from "@/components/taxonomy/ConceptShell"
import { ConceptStage } from "@/components/taxonomy/ConceptStage"
import { RankConstellation } from "@/components/taxonomy/RankConstellation"
import { DiveComputer } from "@/components/taxonomy/DiveComputer"
import { OrbitalTrail } from "@/components/taxonomy/AncestorRail"

export default function ConstellationConceptPage() {
  const [lens, setLens] = useState<TaxonomyLens>("catalog")
  const [selectedTaxid, setSelectedTaxid] = useState<number | null>(null)

  const focus = getMammaliaRow()
  const stars = getOrdersUnderMammalia()
  const ancestors = getMammaliaAncestors()
  const { total, withData } = rankNodeCounts(focus, "order")
  const selected = useMemo(
    () => stars.find((s) => s.taxid === selectedTaxid) ?? focus,
    [stars, selectedTaxid, focus],
  )

  return (
    <ConceptShell
      title="Rank Constellation"
      description={`${withData}/${total} orders with catalog data under Mammalia — sized by NCBI species, colored by active lens.`}
      focusRow={focus}
      currentPath="/taxonomy/concepts/constellation"
      lens={lens}
      onLensChange={setLens}
    >
      <ConceptStage
        depthHue={160 + focus.depth_from_eukaryota * 2}
        viz={
          <div className="flex min-w-0 flex-col items-center gap-3">
            <OrbitalTrail ancestors={ancestors} focusTaxid={focus.taxid} />
            <RankConstellation
              focus={focus}
              stars={stars}
              lens={lens}
              selectedTaxid={selectedTaxid}
              onSelect={(row) => setSelectedTaxid(row.taxid)}
            />
          </div>
        }
        panel={<DiveComputer row={selected} />}
      />
    </ConceptShell>
  )
}

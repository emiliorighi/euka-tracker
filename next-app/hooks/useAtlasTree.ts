"use client"

import { useCallback, useMemo, useState } from "react"
import {
  EUKARYOTA_TAXID,
  useAtlasTaxonomyStore,
} from "@/lib/atlas-taxonomy"

export function useAtlasTree(initialTaxid = EUKARYOTA_TAXID) {
  const [selectedTaxid, setSelectedTaxid] = useState(initialTaxid)
  const [expanded, setExpanded] = useState<Set<number>>(() => new Set([EUKARYOTA_TAXID]))

  const getRowById = useAtlasTaxonomyStore((s) => s.getRowById)
  const getAncestorsOf = useAtlasTaxonomyStore((s) => s.getAncestorsOf)

  const selected = useMemo(
    () => getRowById(selectedTaxid),
    [getRowById, selectedTaxid],
  )

  const expandPathTo = useCallback(
    (taxid: number) => {
      const chain = getAncestorsOf(taxid)
      setExpanded((prev) => {
        const next = new Set(prev)
        for (const row of chain) next.add(row.taxid)
        return next
      })
    },
    [getAncestorsOf],
  )

  const select = useCallback(
    (taxid: number) => {
      expandPathTo(taxid)
      setSelectedTaxid(taxid)
    },
    [expandPathTo],
  )

  const isExpanded = useCallback((taxid: number) => expanded.has(taxid), [expanded])

  return {
    selectedTaxid,
    selected,
    expanded,
    select,
    expandPathTo,
    isExpanded,
  }
}

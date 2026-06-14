"use client"

import { useCallback, useEffect, useMemo, useState } from "react"
import { getParentBookmark } from "@/lib/taxonomy/focus-nav"
import { buildLitTreeRows } from "@/lib/taxonomy/lit-tree"
import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import { findRowIndex } from "@/components/taxonomy/lit-tree/lit-tree-utils"

export function useLitTreeNav(initialTaxid: number) {
  const [focusTaxid, setFocusTaxid] = useState(initialTaxid)
  const [selectedTaxid, setSelectedTaxid] = useState(initialTaxid)
  const [focusExpanded, setFocusExpanded] = useState(true)

  const tree = useMemo(() => buildLitTreeRows(focusTaxid), [focusTaxid])
  const { rows, hasMoreAncestors, rootTaxid } = tree

  useEffect(() => {
    setSelectedTaxid(focusTaxid)
    setFocusExpanded(true)
  }, [focusTaxid])

  const jump = useCallback((taxid: number) => {
    if (taxid === focusTaxid) return
    setFocusTaxid(taxid)
  }, [focusTaxid])

  const drill = useCallback((taxid: number) => {
    if (taxid === focusTaxid) return
    setFocusTaxid(taxid)
  }, [focusTaxid])

  const ascend = useCallback(() => {
    const parent = getParentBookmark(focusTaxid)
    if (!parent) return
    setFocusTaxid(parent.taxid)
  }, [focusTaxid])

  const activateRow = useCallback(
    (row: TaxonRollup, role: "ancestor" | "focus" | "child") => {
      setSelectedTaxid(row.taxid)
      if (role === "ancestor") jump(row.taxid)
      else if (role === "child") drill(row.taxid)
    },
    [jump, drill],
  )

  const cycleSelection = useCallback(
    (delta: number) => {
      if (rows.length === 0) return
      const idx = findRowIndex(rows, selectedTaxid)
      const start = idx >= 0 ? idx : findRowIndex(rows, focusTaxid)
      const next = Math.max(0, Math.min(rows.length - 1, (start >= 0 ? start : 0) + delta))
      setSelectedTaxid(rows[next]!.row.taxid)
    },
    [rows, selectedTaxid, focusTaxid],
  )

  const activateSelected = useCallback(() => {
    const idx = findRowIndex(rows, selectedTaxid)
    if (idx < 0) return
    const treeRow = rows[idx]!
    if (treeRow.role === "focus") {
      if (!focusExpanded) setFocusExpanded(true)
      return
    }
    activateRow(treeRow.row, treeRow.role)
  }, [rows, selectedTaxid, focusExpanded, activateRow])

  return {
    focusTaxid,
    selectedTaxid,
    focusExpanded,
    setFocusExpanded,
    rows,
    hasMoreAncestors,
    rootTaxid,
    jump,
    drill,
    ascend,
    activateRow,
    cycleSelection,
    activateSelected,
  }
}

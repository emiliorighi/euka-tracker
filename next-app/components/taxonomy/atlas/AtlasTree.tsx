"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import {
  EUKARYOTA_TAXID,
  getAtlasChildrenOf,
  getAtlasEukaryotaRow,
  getAtlasRowById,
} from "@/lib/atlas-taxonomy"
import { AtlasTreeConnectors, type AtlasTreeEdge } from "./AtlasTreeConnectors"
import { AtlasTreeSelectedPin } from "./AtlasTreeSelectedPin"
import { AtlasTreeVirtualList } from "./AtlasTreeVirtualList"
import { getSelectionPath } from "./atlas-tree-path"
import {
  buildAtlasTreeLayoutFromTree,
  computeHiddenRowTaxids,
  computePinState,
} from "./atlas-tree-layout-model"
import { cn } from "@/lib/utils"

function collectVisibleEdges(
  taxid: number,
  depth: number,
  isExpanded: (id: number) => boolean,
  out: AtlasTreeEdge[] = [],
): AtlasTreeEdge[] {
  if (!isExpanded(taxid)) return out
  const parent = getAtlasRowById(taxid)
  for (const child of getAtlasChildrenOf(taxid)) {
    out.push({
      parentTaxid: taxid,
      parentRank: parent?.rank ?? "",
      parentDepth: depth,
      childTaxid: child.taxid,
      childRank: child.rank,
    })
    collectVisibleEdges(child.taxid, depth + 1, isExpanded, out)
  }
  return out
}

export function AtlasTree({
  selectedTaxid,
  isExpanded,
  onSelect,
  className,
}: {
  selectedTaxid: number
  isExpanded: (taxid: number) => boolean
  onSelect: (taxid: number) => void
  className?: string
}) {
  const scrollRef = useRef<HTMLDivElement>(null)
  const [scrollElement, setScrollElement] = useState<HTMLDivElement | null>(null)
  const [scrollTop, setScrollTop] = useState(0)
  const [fontSizePx, setFontSizePx] = useState(16)

  const root = getAtlasRowById(EUKARYOTA_TAXID) ?? getAtlasEukaryotaRow()
  const selectedRow = useMemo(() => getAtlasRowById(selectedTaxid), [selectedTaxid])
  const selectionPath = useMemo(() => getSelectionPath(selectedTaxid), [selectedTaxid])

  const layout = useMemo(
    () => buildAtlasTreeLayoutFromTree(root.taxid, isExpanded, fontSizePx),
    [root.taxid, isExpanded, fontSizePx],
  )

  const pinState = useMemo(
    () => computePinState(layout, scrollTop, selectionPath, selectedTaxid),
    [layout, scrollTop, selectionPath, selectedTaxid],
  )

  const pinBandHiddenTaxids = useMemo(
    () => computeHiddenRowTaxids(layout, pinState, selectedTaxid),
    [layout, pinState, selectedTaxid],
  )

  const edges = useMemo(
    () => collectVisibleEdges(root.taxid, 0, isExpanded),
    [root.taxid, isExpanded],
  )

  const handleScroll = useCallback(() => {
    const el = scrollRef.current
    if (el) setScrollTop(el.scrollTop)
  }, [])

  useEffect(() => {
    const panel = scrollRef.current
    if (!panel) return
    setScrollTop(panel.scrollTop)
    const ro = new ResizeObserver(() => {
      const fs = parseFloat(getComputedStyle(panel).fontSize) || 16
      setFontSizePx(fs)
    })
    ro.observe(panel)
    return () => ro.disconnect()
  }, [])

  return (
    <div
      ref={(el) => {
        scrollRef.current = el
        setScrollElement(el)
      }}
      className={cn("atlas-tree-panel min-h-0 w-full overflow-auto", className)}
      onScroll={handleScroll}
    >
      <div
        className="relative min-w-full w-max"
        style={{ minHeight: layout.contentHeight, minWidth: layout.contentWidth }}
      >
        {selectedRow && (
          <AtlasTreeSelectedPin
            row={selectedRow}
            active={pinState.pinActive}
            onSelect={onSelect}
          />
        )}
        <AtlasTreeConnectors
          layout={layout}
          edges={edges}
          selectedTaxid={selectedTaxid}
          pin={pinState.pin}
          pinActive={pinState.pinActive}
          scrollElement={scrollElement}
        />
        <nav className="atlas-tree relative z-[2] w-full pointer-events-none" aria-label="Taxonomy hierarchy">
          <AtlasTreeVirtualList
            layout={layout}
            scrollElement={scrollElement}
            selectedTaxid={selectedTaxid}
            pinActive={pinState.pinActive}
            pinBandHiddenTaxids={pinBandHiddenTaxids}
            onSelect={onSelect}
          />
        </nav>
      </div>
    </div>
  )
}

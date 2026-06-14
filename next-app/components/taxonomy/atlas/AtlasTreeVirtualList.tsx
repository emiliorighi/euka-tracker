"use client"

import { useVirtualizer } from "@tanstack/react-virtual"
import { AtlasTreeRow } from "./AtlasTreeRow"
import type { AtlasTreeLayout } from "./atlas-tree-layout-model"

export function AtlasTreeVirtualList({
  layout,
  scrollElement,
  selectedTaxid,
  pinActive,
  pinBandHiddenTaxids,
  onSelect,
}: {
  layout: AtlasTreeLayout
  scrollElement: HTMLElement | null
  selectedTaxid: number
  pinActive: boolean
  pinBandHiddenTaxids: ReadonlySet<number>
  onSelect: (taxid: number) => void
}) {
  const virtualizer = useVirtualizer({
    count: layout.flatRows.length,
    getScrollElement: () => scrollElement,
    estimateSize: () => layout.metrics.rowHeightPx,
    overscan: 10,
  })

  return (
    <div
      className="relative w-full"
      style={{ height: layout.contentHeight, minWidth: layout.contentWidth }}
    >
      {virtualizer.getVirtualItems().map((virtualRow) => {
        const flatRow = layout.flatRows[virtualRow.index]
        if (!flatRow) return null
        return (
          <div
            key={flatRow.taxid}
            className="absolute left-0 top-0 w-full"
            style={{
              height: virtualRow.size,
              transform: `translateY(${virtualRow.start}px)`,
            }}
          >
            <AtlasTreeRow
              flatRow={flatRow}
              selectedTaxid={selectedTaxid}
              pinActive={pinActive}
              hidePinBand={pinBandHiddenTaxids.has(flatRow.taxid)}
              onSelect={onSelect}
            />
          </div>
        )
      })}
    </div>
  )
}

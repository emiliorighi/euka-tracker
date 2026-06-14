"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { EUKARYOTA_TAXID, getAtlasRowById } from "@/lib/atlas-taxonomy"
import { CladeTooltipCard } from "@/components/taxonomy/CladeTooltip"
import { getSelectionPath } from "./atlas-tree-path"
import type { AtlasPinContext, AtlasTreeLayout } from "./atlas-tree-layout-model"
import {
  AtlasTreeConnectorsCanvas,
  hitTestConnectorAtPoint,
} from "./AtlasTreeConnectorsCanvas"
import {
  buildConnectorSegments,
  type AtlasConnectorSegment,
  type AtlasTreeEdge,
} from "./atlas-tree-segments"
import { cn } from "@/lib/utils"

export type { AtlasTreeEdge }

function segmentsEqual(prev: AtlasConnectorSegment[], next: AtlasConnectorSegment[]): boolean {
  return (
    prev.length === next.length &&
    prev.every((p, i) => {
      const n = next[i]!
      return (
        p.ownerTaxid === n.ownerTaxid &&
        p.childTaxid === n.childTaxid &&
        p.axis === n.axis &&
        p.role === n.role &&
        p.x1 === n.x1 &&
        p.y1 === n.y1 &&
        p.x2 === n.x2 &&
        p.y2 === n.y2
      )
    })
  )
}

export function AtlasTreeConnectors({
  layout,
  edges,
  selectedTaxid,
  pin,
  pinActive,
  scrollElement,
  className,
}: {
  layout: AtlasTreeLayout
  edges: AtlasTreeEdge[]
  selectedTaxid: number
  pin: AtlasPinContext | null
  pinActive: boolean
  scrollElement: HTMLElement | null
  className?: string
}) {
  const [segments, setSegments] = useState<AtlasConnectorSegment[]>([])
  const [hoveredParentTaxid, setHoveredParentTaxid] = useState<number | null>(null)
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 })

  const selectionPath = useMemo(() => getSelectionPath(selectedTaxid), [selectedTaxid])
  const pathTaxids = useMemo(
    () => new Set(selectionPath.map((row) => row.taxid)),
    [selectionPath],
  )

  const recompute = useCallback(() => {
    const nextSegments = buildConnectorSegments({
      layout,
      edges,
      selectionPath,
      pathTaxids: pinActive ? pathTaxids : null,
      pin: pinActive ? pin : null,
      selectedTaxid,
      rootTaxid: EUKARYOTA_TAXID,
    })
    setSegments((prev) => (segmentsEqual(prev, nextSegments) ? prev : nextSegments))
  }, [layout, edges, selectedTaxid, selectionPath, pathTaxids, pinActive, pin])

  useEffect(() => {
    recompute()
  }, [recompute])

  const hoveredRow = useMemo(
    () => (hoveredParentTaxid != null ? getAtlasRowById(hoveredParentTaxid) : null),
    [hoveredParentTaxid],
  )

  const segmentsRef = useRef(segments)
  segmentsRef.current = segments

  useEffect(() => {
    const panel = scrollElement
    if (!panel) return
    const content = panel.firstElementChild as HTMLElement | null

    const onPointerMove = (e: PointerEvent) => {
      if (!content) return
      const rect = content.getBoundingClientRect()
      const px = e.clientX - rect.left
      const py = e.clientY - rect.top
      const hit = hitTestConnectorAtPoint(px, py, segmentsRef.current)
      setHoveredParentTaxid(hit)
      if (hit != null) setTooltipPos({ x: e.clientX, y: e.clientY })
    }

    const onPointerLeave = () => setHoveredParentTaxid(null)

    panel.addEventListener("pointermove", onPointerMove)
    panel.addEventListener("pointerleave", onPointerLeave)
    return () => {
      panel.removeEventListener("pointermove", onPointerMove)
      panel.removeEventListener("pointerleave", onPointerLeave)
    }
  }, [scrollElement])

  return (
    <>
      <AtlasTreeConnectorsCanvas
        segments={segments}
        contentWidth={layout.contentWidth}
        contentHeight={layout.contentHeight}
        hoveredParentTaxid={hoveredParentTaxid}
        className={cn(
          "atlas-tree-connectors absolute left-0 top-0 pointer-events-none",
          pinActive ? "z-[25]" : "z-[3]",
          className,
        )}
      />
      {hoveredRow && (
        <div
          className="atlas-connector-tooltip pointer-events-none fixed z-[70]"
          style={{ left: tooltipPos.x + 14, top: tooltipPos.y + 8 }}
          role="tooltip"
        >
          <CladeTooltipCard row={hoveredRow} />
        </div>
      )}
    </>
  )
}

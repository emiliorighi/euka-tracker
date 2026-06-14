"use client"

import { useCallback, useEffect, useMemo, useRef, useState, type RefObject } from "react"
import { depthLineColor, type LitTreeRow } from "@/lib/taxonomy/lit-tree"
import { CladeTooltipCard } from "@/components/taxonomy/CladeTooltip"
import { getRowById } from "@/lib/taxonomy-mock"
import { cn } from "@/lib/utils"

type RowGeometry = {
  taxid: number
  depth: number
  segmentTaxid?: number
  y: number
  x: number
  role: LitTreeRow["role"]
}

type SegmentGeometry = {
  taxid: number
  depth: number
  x1: number
  y1: number
  x2: number
  y2: number
}

function computeGeometry(
  panelEl: HTMLElement,
  rowEls: Map<number, HTMLElement>,
  rows: LitTreeRow[],
): { rowGeoms: RowGeometry[]; segments: SegmentGeometry[] } {
  const panelRect = panelEl.getBoundingClientRect()
  const rowGeoms: RowGeometry[] = []

  for (const treeRow of rows) {
    const el = rowEls.get(treeRow.row.taxid)
    if (!el) continue
    const card = el.querySelector(".lit-tree-row-card") ?? el
    const rect = card.getBoundingClientRect()
    const x = rect.left - panelRect.left
    const y = rect.top - panelRect.top + rect.height / 2
    rowGeoms.push({
      taxid: treeRow.row.taxid,
      depth: treeRow.depth,
      segmentTaxid: treeRow.segmentTaxid,
      y,
      x,
      role: treeRow.role,
    })
  }

  const segments: SegmentGeometry[] = []
  const trunkX = 12

  for (let i = 0; i < rowGeoms.length; i++) {
    const current = rowGeoms[i]!
    if (current.segmentTaxid == null) continue

    const prev = i > 0 ? rowGeoms[i - 1] : null
    const y1 = prev ? prev.y : current.y - 20
    const y2 = current.y

    segments.push({
      taxid: current.segmentTaxid,
      depth: current.depth,
      x1: trunkX + current.depth * 8,
      y1,
      x2: trunkX + current.depth * 8,
      y2,
    })
  }

  for (const geom of rowGeoms) {
    const segX = trunkX + geom.depth * 8
    segments.push({
      taxid: geom.role === "child" ? geom.taxid : geom.segmentTaxid ?? geom.taxid,
      depth: geom.depth,
      x1: segX,
      y1: geom.y,
      x2: geom.x - 4,
      y2: geom.y,
    })
  }

  return { rowGeoms, segments }
}

export function LitTreeGutter({
  rows,
  rowRefs,
  panelRef,
  rowVersion = 0,
  className,
}: {
  rows: LitTreeRow[]
  rowRefs: Map<number, HTMLElement>
  panelRef: RefObject<HTMLElement | null>
  rowVersion?: number
  className?: string
}) {
  const [segments, setSegments] = useState<SegmentGeometry[]>([])
  const [hoveredTaxid, setHoveredTaxid] = useState<number | null>(null)
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 })
  const svgRef = useRef<SVGSVGElement>(null)

  const remeasure = useCallback(() => {
    const panel = panelRef.current
    if (!panel || rowRefs.size === 0) return
    const { segments: next } = computeGeometry(panel, rowRefs, rows)
    setSegments((prev) => {
      if (prev.length === next.length && prev.every((p, i) => {
        const n = next[i]!
        return p.taxid === n.taxid && p.x1 === n.x1 && p.y1 === n.y1 && p.x2 === n.x2 && p.y2 === n.y2
      })) {
        return prev
      }
      return next
    })
  }, [panelRef, rowRefs, rows])

  useEffect(() => {
    remeasure()
    const panel = panelRef.current
    if (!panel) return

    const ro = new ResizeObserver(() => remeasure())
    ro.observe(panel)
    rowRefs.forEach((el) => ro.observe(el))

    const onScroll = () => remeasure()
    panel.addEventListener("scroll", onScroll, { passive: true })
    window.addEventListener("resize", remeasure)

    return () => {
      ro.disconnect()
      panel.removeEventListener("scroll", onScroll)
      window.removeEventListener("resize", remeasure)
    }
  }, [remeasure, panelRef, rowRefs, rows, rowVersion])

  const hoveredRow = useMemo(
    () => (hoveredTaxid != null ? getRowById(hoveredTaxid) : null),
    [hoveredTaxid],
  )

  const segmentPaths = useMemo(() => {
    const seen = new Set<string>()
    return segments.filter((seg) => {
      const key = `${seg.taxid}-${seg.x1}-${seg.y1}-${seg.x2}-${seg.y2}`
      if (seen.has(key)) return false
      seen.add(key)
      return seg.y2 >= seg.y1 - 1
    })
  }, [segments])

  return (
    <>
      <svg
        ref={svgRef}
        className={cn("lit-tree-gutter pointer-events-none absolute inset-0 z-[2] h-full w-full overflow-visible", className)}
        aria-hidden
      >
        {segmentPaths.map((seg, i) => {
          const isVertical = Math.abs(seg.x2 - seg.x1) < 1
          if (!isVertical) {
            return (
              <line
                key={`elbow-${seg.taxid}-${i}`}
                x1={seg.x1}
                y1={seg.y1}
                x2={seg.x2}
                y2={seg.y2}
                stroke={depthLineColor(seg.depth, 0.35)}
                strokeWidth={1.5}
                strokeLinecap="round"
              />
            )
          }
          return (
            <g key={`seg-${seg.taxid}-${i}`}>
              <line
                x1={seg.x1}
                y1={seg.y1}
                x2={seg.x2}
                y2={seg.y2}
                stroke={depthLineColor(seg.depth, hoveredTaxid === seg.taxid ? 0.85 : 0.45)}
                strokeWidth={hoveredTaxid === seg.taxid ? 2.5 : 1.5}
                strokeLinecap="round"
              />
              <line
                data-tree-segment={seg.taxid}
                x1={seg.x1}
                y1={seg.y1}
                x2={seg.x2}
                y2={seg.y2}
                stroke="transparent"
                strokeWidth={12}
                className="pointer-events-auto cursor-pointer"
                onPointerEnter={(e) => {
                  setHoveredTaxid(seg.taxid)
                  setTooltipPos({ x: e.clientX, y: e.clientY })
                }}
                onPointerMove={(e) => setTooltipPos({ x: e.clientX, y: e.clientY })}
                onPointerLeave={() => setHoveredTaxid(null)}
              />
            </g>
          )
        })}
      </svg>
      {hoveredRow && (
        <div
          data-tree-segment-tooltip
          className="lit-tree-segment-tooltip pointer-events-none fixed z-50"
          style={{ left: tooltipPos.x + 12, top: tooltipPos.y + 8 }}
          role="tooltip"
        >
          <CladeTooltipCard row={hoveredRow} extra={`Depth ${hoveredRow.depth_from_eukaryota}`} />
        </div>
      )}
    </>
  )
}

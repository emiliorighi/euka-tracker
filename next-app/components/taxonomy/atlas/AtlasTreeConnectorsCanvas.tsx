"use client"

import { useCallback, useEffect, useRef } from "react"
import { getRankColor } from "@/lib/taxonomy/rank-colors"
import type { AtlasConnectorSegment } from "./atlas-tree-segments"

export type AtlasConnectorDebug = {
  segments: AtlasConnectorSegment[]
}

declare global {
  interface Window {
    __ATLAS_CONNECTOR_DEBUG__?: AtlasConnectorDebug
  }
}

const HIT_VERTICAL = 16
const HIT_HORIZONTAL = 12

function distToSegment(px: number, py: number, seg: AtlasConnectorSegment): number {
  const { x1, y1, x2, y2 } = seg
  if (seg.axis === "vertical") {
    const minY = Math.min(y1, y2)
    const maxY = Math.max(y1, y2)
    if (py < minY || py > maxY) {
      return Math.min(
        Math.hypot(px - x1, py - minY),
        Math.hypot(px - x1, py - maxY),
      )
    }
    return Math.abs(px - x1)
  }
  const minX = Math.min(x1, x2)
  const maxX = Math.max(x1, x2)
  if (px < minX || px > maxX) {
    return Math.min(
      Math.hypot(px - minX, py - y1),
      Math.hypot(px - maxX, py - y1),
    )
  }
  return Math.abs(py - y1)
}

function hitTestSegment(px: number, py: number, seg: AtlasConnectorSegment): boolean {
  const threshold = seg.axis === "vertical" ? HIT_VERTICAL / 2 : HIT_HORIZONTAL / 2
  return distToSegment(px, py, seg) <= threshold
}

/** Content-space hit test; returns closest segment owner taxid or null. */
export function hitTestConnectorAtPoint(
  px: number,
  py: number,
  segments: AtlasConnectorSegment[],
): number | null {
  let hit: number | null = null
  let bestDist = Infinity
  for (const seg of segments) {
    if (!hitTestSegment(px, py, seg)) continue
    const d = distToSegment(px, py, seg)
    if (d < bestDist) {
      bestDist = d
      hit = seg.ownerTaxid
    }
  }
  return hit
}

function drawSegments(
  ctx: CanvasRenderingContext2D,
  segments: AtlasConnectorSegment[],
  hoveredParentTaxid: number | null,
  dpr: number,
) {
  const scale = 1 / dpr
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0)
  ctx.clearRect(0, 0, ctx.canvas.width * scale, ctx.canvas.height * scale)

  for (const seg of segments) {
    const active = hoveredParentTaxid === seg.ownerTaxid
    const isFlat = seg.role === "flatPath"
    const isPinnedCard = seg.role === "toCard" && seg.onPinRow
    const isHorizontal = seg.axis === "horizontal"
    const opacity = active ? 0.92 : isFlat ? 0.55 : 0.42

    ctx.beginPath()
    ctx.moveTo(seg.x1, seg.y1)
    ctx.lineTo(seg.x2, seg.y2)
    ctx.strokeStyle = getRankColor(seg.ownerRank, opacity)
    ctx.lineWidth = active ? 2.25 : 1.5
    ctx.lineCap =
      isHorizontal && (seg.onPinRow || isFlat || isPinnedCard) ? "butt" : "round"
    ctx.stroke()
  }
}

export function AtlasTreeConnectorsCanvas({
  segments,
  contentWidth,
  contentHeight,
  hoveredParentTaxid,
  className,
}: {
  segments: AtlasConnectorSegment[]
  contentWidth: number
  contentHeight: number
  hoveredParentTaxid: number | null
  className?: string
}) {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const segmentsRef = useRef(segments)
  segmentsRef.current = segments

  useEffect(() => {
    if (typeof window !== "undefined") {
      window.__ATLAS_CONNECTOR_DEBUG__ = { segments }
    }
  }, [segments])

  const paint = useCallback(() => {
    const canvas = canvasRef.current
    if (!canvas) return
    const dpr = window.devicePixelRatio || 1
    canvas.width = Math.ceil(contentWidth * dpr)
    canvas.height = Math.ceil(contentHeight * dpr)
    canvas.style.width = `${contentWidth}px`
    canvas.style.height = `${contentHeight}px`
    const ctx = canvas.getContext("2d")
    if (!ctx) return
    drawSegments(ctx, segmentsRef.current, hoveredParentTaxid, dpr)
  }, [contentWidth, contentHeight, hoveredParentTaxid])

  useEffect(() => {
    paint()
  }, [paint, segments, hoveredParentTaxid])

  return (
    <canvas
      ref={canvasRef}
      className={className}
      data-atlas-connector-canvas=""
      data-segment-count={segments.length}
      aria-hidden
    />
  )
}

/** Test helper: segments with flat/pinned metadata matching legacy SVG attrs. */
export function connectorDebugEntries(segments: AtlasConnectorSegment[]) {
  return segments.map((seg) => ({
    ...seg,
    flat: seg.role === "flatPath" ? seg.ownerTaxid : undefined,
    pinned: seg.role === "toCard" && seg.onPinRow ? seg.ownerTaxid : undefined,
  }))
}

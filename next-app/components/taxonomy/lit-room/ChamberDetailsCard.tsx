"use client"

import type { RefObject } from "react"
import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import type { LitRoomMode } from "@/lib/taxonomy/lit-room"
import type { ChamberMotionPhase } from "@/hooks/useChamberMotion"
import { ChamberHeadline } from "./ChamberHeadline"
import { CoverageArc } from "./CoverageArc"
import { FunnelStrip } from "./FunnelStrip"
import { GhostVeil } from "./GhostVeil"
import { cn } from "@/lib/utils"

export function ChamberDetailsCard({
  row,
  mode,
  detailsRef,
  motionPhase,
  heroVisible,
  className,
}: {
  row: TaxonRollup
  mode: LitRoomMode
  detailsRef?: RefObject<HTMLDivElement | null>
  motionPhase?: ChamberMotionPhase
  heroVisible?: boolean
  className?: string
}) {
  const isSettling = motionPhase === "settle"
  const isPrepare = motionPhase === "prepare" || motionPhase === "morph" || motionPhase === "commit"

  return (
    <div
      className={cn(
        "chamber-details-slot",
        isPrepare && !heroVisible && "details-slot-prepare",
        className,
      )}
    >
      <div
        ref={detailsRef}
        className={cn(
          "chamber-details-card vt-lit-details relative min-w-0 overflow-hidden rounded-xl border border-white/10 bg-black/20 backdrop-blur-sm",
          isSettling && heroVisible && "details-card-handoff",
        )}
      >
        <span data-lit-chamber-title tabIndex={-1} className="sr-only">
          {row.scientific_name}
        </span>
        <div className="chamber-details-glow pointer-events-none absolute inset-0 rounded-xl" aria-hidden />
        <div className="relative space-y-4 p-4 md:p-5">
          <ChamberHeadline row={row} />
          <GhostVeil row={row} />
          <div className="grid gap-4 md:grid-cols-[auto_1fr] md:items-start">
            <CoverageArc row={row} glow={mode.chamberGlow} />
            <FunnelStrip row={row} />
          </div>
        </div>
      </div>
    </div>
  )
}

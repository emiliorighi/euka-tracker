"use client"

import type { RefObject, ReactNode } from "react"
import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import type { LitRoomMode } from "@/lib/taxonomy/lit-room"
import type { ChamberMotionDirection, ChamberMotionPhase } from "@/hooks/useChamberMotion"
import { ChamberDetailsCard } from "./ChamberDetailsCard"
import { cn } from "@/lib/utils"

export function ChamberStack({
  row,
  mode,
  detailsRef,
  motionPhase = "idle",
  motionDirection,
  heroVisible = true,
  eclipsed,
  parent,
  children,
  floor,
  className,
}: {
  row: TaxonRollup
  mode: LitRoomMode
  detailsRef?: RefObject<HTMLDivElement | null>
  motionPhase?: ChamberMotionPhase
  motionDirection?: ChamberMotionDirection | null
  heroVisible?: boolean
  eclipsed?: boolean
  parent?: ReactNode
  children?: ReactNode
  floor?: ReactNode
  className?: string
}) {
  return (
    <div
      className={cn(
        "chamber-stack relative min-h-[min(70vh,36rem)] min-w-0 overflow-hidden rounded-2xl border border-white/10",
        eclipsed && "chamber-eclipsed",
        mode.isGhost && "chamber-ghost",
        className,
      )}
      data-motion={motionPhase}
      data-direction={motionDirection ?? undefined}
      style={
        {
          "--chamber-hue": mode.depthHue,
          "--chamber-glow": mode.chamberGlow,
          "--fog-opacity": mode.isGhost ? 0.65 : 0.15,
        } as React.CSSProperties
      }
    >
      <div className="chamber-room-glow" aria-hidden />
      <div className="chamber-room-vignette" aria-hidden />
      {mode.isGhost && <div className="chamber-room-fog" aria-hidden />}

      <div className="chamber-stack-interior relative z-[1] flex min-h-full flex-col gap-3 p-3 md:gap-4 md:p-4">
        {parent}
        <ChamberDetailsCard
          row={row}
          mode={mode}
          detailsRef={detailsRef}
          motionPhase={motionPhase}
          heroVisible={heroVisible}
        />
        {children}
        {floor && (
          <section className="chamber-floor-plane mt-auto border-t border-white/10 pt-3" aria-label="Chamber floor">
            {floor}
          </section>
        )}
      </div>
    </div>
  )
}

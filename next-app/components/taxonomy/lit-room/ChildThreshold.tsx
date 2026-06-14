"use client"

import { useEffect, useRef, useState } from "react"
import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import { getChildDeck } from "@/lib/taxonomy/focus-nav"
import { rankBreakdownLabel } from "@/lib/taxonomy/ranks"
import type { ChamberMotionPhase } from "@/hooks/useChamberMotion"
import { ThresholdCard } from "./ThresholdCard"
import { DustPanel } from "./DustPanel"
import { cn } from "@/lib/utils"

export function ChildThreshold({
  focus,
  focusTaxid,
  selectedIndex,
  onSelectIndex,
  onDrill,
  isBusy,
  motionPhase = "idle",
  sourceTaxid,
  className,
}: {
  focus: TaxonRollup
  focusTaxid: number
  selectedIndex: number
  onSelectIndex: (index: number) => void
  onDrill: (row: TaxonRollup, sourceEl: HTMLButtonElement | null) => void
  isBusy?: boolean
  motionPhase?: ChamberMotionPhase
  sourceTaxid?: number | null
  className?: string
}) {
  const { visible, hidden, hiddenCount } = getChildDeck(focusTaxid)
  const [dustOpen, setDustOpen] = useState(false)
  const trackRef = useRef<HTMLDivElement>(null)
  const rankLabel = rankBreakdownLabel(focus)
  const isSettling = motionPhase !== "idle"

  useEffect(() => {
    setDustOpen(false)
  }, [focusTaxid])

  useEffect(() => {
    const card = trackRef.current?.querySelector(`[data-doorway][data-selected="true"]`)
    card?.scrollIntoView({ block: "nearest", inline: "center", behavior: "smooth" })
  }, [selectedIndex])

  if (visible.length === 0 && hiddenCount === 0) {
    return (
      <div
        className={cn(
          "child-threshold-empty rounded-xl border border-dashed border-white/10 px-3 py-4 text-center text-sm text-muted-foreground",
          className,
        )}
      >
        Leaf chamber — no child thresholds
      </div>
    )
  }

  return (
    <section className={cn("child-threshold min-w-0 space-y-2", className)} aria-label="Child thresholds">
      <div className="flex items-baseline justify-between gap-2 px-0.5">
        <h3 className="text-sm font-medium tracking-wide text-foreground/90">Thresholds</h3>
        {rankLabel && <p className="truncate text-xs text-muted-foreground">{rankLabel}</p>}
      </div>
      <div
        ref={trackRef}
        data-focus-key={focusTaxid}
        data-settling={isSettling ? "true" : undefined}
        className="child-threshold-track flex gap-2 overflow-x-auto overscroll-x-contain pb-1 pt-0.5"
      >
        {visible.map((row, i) => (
          <ThresholdCard
            key={row.taxid}
            row={row}
            selected={selectedIndex === i}
            isMorphSource={sourceTaxid === row.taxid}
            onSelect={() => onSelectIndex(i)}
            onClick={(e) => {
              if (isBusy) return
              onDrill(row, e.currentTarget)
            }}
          />
        ))}
        {hiddenCount > 0 && (
          <button
            type="button"
            disabled={isBusy}
            onClick={() => setDustOpen((o) => !o)}
            className="dust-chip threshold-card flex h-[5.5rem] w-[5rem] shrink-0 snap-center flex-col items-center justify-center rounded-xl border border-dashed border-muted-foreground/30 bg-white/[0.02] hover:bg-white/5 disabled:opacity-50"
          >
            <span className="text-xs font-medium">Dust</span>
            <span className="font-mono text-sm tabular-nums text-muted-foreground">+{hiddenCount}</span>
          </button>
        )}
      </div>
      {dustOpen && hidden.length > 0 && (
        <DustPanel
          rows={hidden}
          disabled={isBusy}
          onDrill={(row) => {
            if (isBusy) return
            onDrill(row, null)
          }}
        />
      )}
    </section>
  )
}

"use client"

import type { RefObject } from "react"
import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import { DiveComputer } from "../DiveComputer"
import { FunnelCathedral } from "../FunnelCathedral"
import { cn } from "@/lib/utils"

export function FocusHero({
  row,
  heroRef,
  hidden,
  className,
}: {
  row: TaxonRollup
  heroRef?: RefObject<HTMLDivElement | null>
  hidden?: boolean
  className?: string
}) {
  const hue = 160 + row.depth_from_eukaryota * 2

  return (
    <div
      ref={heroRef}
      className={cn(
        "focus-hero-crossfade vt-focus-hero min-w-0 overflow-hidden rounded-xl border border-border/50 p-3 md:p-4",
        hidden && "is-hidden",
        className,
      )}
      style={{ backgroundColor: `oklch(0.16 0.012 ${hue} / 0.35)` }}
    >
      <span data-focus-title tabIndex={-1} className="sr-only">
        {row.scientific_name}
      </span>
      <DiveComputer row={row} className="border-0 bg-transparent p-0 backdrop-blur-none" />
      <div className="overflow-hidden">
        <FunnelCathedral row={row} maxHeight={200} />
      </div>
    </div>
  )
}

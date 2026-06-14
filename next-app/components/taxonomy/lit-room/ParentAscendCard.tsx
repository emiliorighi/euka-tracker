"use client"

import { forwardRef } from "react"
import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import { getParentBookmark } from "@/lib/taxonomy/focus-nav"
import { CladeCardShell } from "./CladeCardShell"
import { LitScientificName } from "./LitScientificName"
import { cn } from "@/lib/utils"

export const ParentAscendCard = forwardRef<
  HTMLButtonElement,
  {
    focusTaxid: number
    onAscend: (parent: TaxonRollup, el: HTMLButtonElement) => void
    disabled?: boolean
    isMorphSource?: boolean
    variant?: "full" | "compact"
    className?: string
  }
>(function ParentAscendCard(
  { focusTaxid, onAscend, disabled, isMorphSource, variant = "full", className },
  ref,
) {
  const parent = getParentBookmark(focusTaxid)
  if (!parent) return null

  return (
    <button
      ref={ref}
      type="button"
      disabled={disabled}
      onClick={(e) => onAscend(parent, e.currentTarget)}
      className={cn(
        "parent-ascend-card threshold-card group w-full text-left transition-transform duration-300 hover:-translate-y-0.5 disabled:opacity-50",
        variant === "compact" && "max-w-xs",
        className,
      )}
      aria-label={`Go up to ${parent.scientific_name}`}
    >
      <CladeCardShell
        row={parent}
        variant="compact"
        badge={
          <span className="absolute left-3 top-1 z-[1] flex items-center gap-1 text-[9px] uppercase tracking-widest text-primary">
            <span aria-hidden>↑</span> Exit
          </span>
        }
        className={cn(
          "border-primary/25 bg-primary/5 hover:border-primary/40",
          isMorphSource && "is-morph-source",
        )}
      >
        <div className="relative space-y-1 pt-2">
          <LitScientificName
            name={
              variant === "compact"
                ? parent.scientific_name.split(" ")[0] ?? parent.scientific_name
                : parent.scientific_name
            }
            className="line-clamp-2 text-xs leading-tight"
          />
          <span className="text-[10px] capitalize text-muted-foreground">{parent.rank}</span>
        </div>
      </CladeCardShell>
    </button>
  )
})

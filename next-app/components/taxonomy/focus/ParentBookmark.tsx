"use client"

import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import { getParentBookmark } from "@/lib/taxonomy/focus-nav"
import { SpineTab } from "./SpineTab"
import { cn } from "@/lib/utils"

export function ParentBookmark({
  focusTaxid,
  onAscend,
  className,
  tabRef,
  disabled,
  variant = "vertical",
}: {
  focusTaxid: number
  onAscend: (parent: TaxonRollup, el: HTMLButtonElement) => void
  className?: string
  tabRef?: React.Ref<HTMLButtonElement>
  disabled?: boolean
  variant?: "vertical" | "horizontal"
}) {
  const parent = getParentBookmark(focusTaxid)

  if (!parent) {
    return null
  }

  if (variant === "horizontal") {
    return (
      <button
        ref={tabRef}
        type="button"
        disabled={disabled}
        onClick={(e) => onAscend(parent, e.currentTarget)}
        className={cn(
          "spine-tab vt-parent-tab shrink-0 rounded-lg border border-primary/35 bg-primary/10 px-3 py-1.5 text-xs text-primary hover:bg-primary/15 disabled:opacity-50",
          className,
        )}
        aria-label={`Go up to ${parent.scientific_name}`}
      >
        ↑ {parent.scientific_name.split(" ")[0]}
      </button>
    )
  }

  return (
    <div className={cn("flex flex-col justify-start", className)}>
      <SpineTab
        row={parent}
        variant="parent"
        disabled={disabled}
        onClick={(e) => onAscend(parent, e.currentTarget)}
        tabRef={tabRef}
        className="vt-parent-tab"
      />
    </div>
  )
}

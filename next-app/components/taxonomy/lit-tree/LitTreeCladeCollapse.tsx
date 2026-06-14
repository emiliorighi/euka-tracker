"use client"

import { ChevronDown } from "lucide-react"
import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import type { LitRoomMode } from "@/lib/taxonomy/lit-room"
import { ChamberDetailsCard } from "@/components/taxonomy/lit-room/ChamberDetailsCard"
import { CladeCardShell } from "@/components/taxonomy/lit-room/CladeCardShell"
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from "@/components/ui/collapsible"
import { cn } from "@/lib/utils"

export function LitTreeCladeCollapse({
  row,
  mode,
  expanded,
  onExpandedChange,
  selected,
  className,
}: {
  row: TaxonRollup
  mode: LitRoomMode
  expanded: boolean
  onExpandedChange: (open: boolean) => void
  selected?: boolean
  className?: string
}) {
  return (
    <Collapsible open={expanded} onOpenChange={onExpandedChange} className={cn("min-w-0", className)}>
      <CollapsibleTrigger
        className={cn(
          "lit-tree-collapse-trigger group relative rounded-xl transition-shadow",
          selected && "ring-2 ring-primary/70 ring-offset-2 ring-offset-background",
          expanded && "mb-2",
        )}
      >
        <CladeCardShell
          row={row}
          variant="compact"
          badge={
            <span
              className={cn(
                "absolute right-3 top-2 z-[1] text-muted-foreground transition-transform duration-200",
                expanded && "rotate-180",
              )}
            >
              <ChevronDown className="size-4" aria-hidden />
            </span>
          }
          className="border-primary/30 bg-primary/5 pr-10"
        />
        <span className="sr-only">{expanded ? "Collapse" : "Expand"} details for {row.scientific_name}</span>
      </CollapsibleTrigger>
      <CollapsibleContent className="lit-tree-collapse-content">
        <ChamberDetailsCard row={row} mode={mode} motionPhase="idle" heroVisible />
      </CollapsibleContent>
    </Collapsible>
  )
}

"use client"

import { useEffect, useRef } from "react"
import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import type { LitRoomMode } from "@/lib/taxonomy/lit-room"
import type { LitTreeRow as LitTreeRowModel } from "@/lib/taxonomy/lit-tree"
import { CladeCardShell } from "@/components/taxonomy/lit-room/CladeCardShell"
import { rowIndentStyle } from "./lit-tree-utils"
import { LitTreeCladeCollapse } from "./LitTreeCladeCollapse"
import { cn } from "@/lib/utils"

export function LitTreeRow({
  treeRow,
  mode,
  selected,
  focusExpanded = true,
  onFocusExpandedChange,
  onActivate,
  onRegister,
  className,
}: {
  treeRow: LitTreeRowModel
  mode: LitRoomMode
  selected?: boolean
  focusExpanded?: boolean
  onFocusExpandedChange?: (open: boolean) => void
  onActivate: (row: TaxonRollup, role: LitTreeRowModel["role"]) => void
  onRegister?: (taxid: number, el: HTMLDivElement | null) => void
  className?: string
}) {
  const localRef = useRef<HTMLDivElement>(null)
  const { row, role, depth } = treeRow

  useEffect(() => {
    onRegister?.(row.taxid, localRef.current)
    return () => onRegister?.(row.taxid, null)
  }, [row.taxid, onRegister])

  return (
    <div
      ref={localRef}
      data-tree-row={row.taxid}
      data-tree-role={role}
      data-tree-depth={depth}
      className={cn("lit-tree-row relative flex min-w-0 py-1.5 pointer-events-none", className)}
      style={rowIndentStyle(depth)}
    >
      <div className="lit-tree-row-card min-w-0 flex-1 pl-3 pointer-events-auto">
        {role === "focus" ? (
          <LitTreeCladeCollapse
            row={row}
            mode={mode}
            expanded={focusExpanded}
            onExpandedChange={onFocusExpandedChange ?? (() => undefined)}
            selected={selected}
          />
        ) : (
          <button
            type="button"
            onClick={() => onActivate(row, role)}
            className={cn(
              "lit-tree-compact-card w-full text-left transition-transform duration-200 hover:-translate-y-0.5",
              selected && "ring-2 ring-primary/70 ring-offset-2 ring-offset-background rounded-xl",
              role === "child" && "lit-tree-child-card",
            )}
          >
            <CladeCardShell
              row={row}
              variant="compact"
              className={cn(
                role === "ancestor" && "opacity-90 hover:border-primary/35",
                role === "child" && "hover:border-primary/40",
              )}
            />
          </button>
        )}
      </div>
    </div>
  )
}

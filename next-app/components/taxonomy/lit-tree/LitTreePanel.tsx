"use client"

import { useCallback, useRef, useState, type ReactNode } from "react"
import type { LitTreeRow } from "@/lib/taxonomy/lit-tree"
import { LitTreeGutter } from "./LitTreeGutter"
import { cn } from "@/lib/utils"

export function LitTreePanel({
  rows,
  rootJump,
  children,
  className,
}: {
  rows: LitTreeRow[]
  rootJump?: { taxid: number; onJump: () => void; disabled?: boolean }
  children: (registerRow: (taxid: number, el: HTMLDivElement | null) => void) => ReactNode
  className?: string
}) {
  const panelRef = useRef<HTMLDivElement>(null)
  const rowRefsMap = useRef(new Map<number, HTMLElement>())
  const [rowVersion, bumpRowVersion] = useState(0)

  const registerRow = useCallback((taxid: number, el: HTMLDivElement | null) => {
    const map = rowRefsMap.current
    const existing = map.get(taxid)
    if (el === existing) return
    if (el) map.set(taxid, el)
    else map.delete(taxid)
    bumpRowVersion((n) => n + 1)
  }, [])

  return (
    <div
      ref={panelRef}
      className={cn(
        "lit-tree-panel relative min-h-0 min-w-0 flex-1 overflow-y-auto overflow-x-hidden rounded-xl border border-white/10 bg-black/10 p-2 md:p-3",
        className,
      )}
    >
      {rootJump && (
        <button
          type="button"
          disabled={rootJump.disabled}
          onClick={rootJump.onJump}
          className="lit-tree-root-jump mb-2 rounded-lg border border-dashed border-primary/30 px-2 py-1 text-[10px] uppercase tracking-widest text-muted-foreground hover:bg-white/5 disabled:opacity-50"
        >
          ↑ Jump to root
        </button>
      )}
      <LitTreeGutter
        rows={rows}
        rowRefs={rowRefsMap.current}
        panelRef={panelRef}
        rowVersion={rowVersion}
      />
      <div className="lit-tree-rows relative z-[1] min-w-0">{children(registerRow)}</div>
    </div>
  )
}

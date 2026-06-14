"use client"

import Link from "next/link"
import { useEffect, useRef, type ReactNode } from "react"
import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import { formatLitDual } from "@/components/taxonomy/lit-room/lit-room-utils"
import { cn } from "@/lib/utils"

export function LitTreeShell({
  focusRow,
  headerExtra,
  children,
}: {
  focusRow?: TaxonRollup
  headerExtra?: ReactNode
  children: ReactNode
}) {
  const liveRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!focusRow || !liveRef.current) return
    liveRef.current.textContent = `${focusRow.scientific_name} — ${formatLitDual(focusRow)}`
  }, [focusRow])

  return (
    <div className="lit-tree-root lit-room-root flex min-h-0 min-w-0 flex-1 flex-col gap-4">
      <header className="lit-tree-header min-w-0 shrink-0 border-b border-border/60 pb-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 space-y-2">
            <Link
              href="/taxonomy/concepts"
              className="inline-flex h-8 items-center rounded-md px-2 text-sm text-muted-foreground transition-colors hover:bg-secondary/60 hover:text-foreground"
            >
              ← Concepts
            </Link>
            <div className="space-y-1">
              <p className="text-[10px] font-medium uppercase tracking-[0.2em] text-primary/80">
                Concept 8
              </p>
              <h1 className="bg-gradient-to-r from-primary via-foreground to-primary/70 bg-clip-text text-xl font-semibold tracking-tight text-transparent">
                The Lit Tree
              </h1>
              <p className="max-w-2xl text-sm text-muted-foreground">
                A vertical collapsed-card tree — depth lines connect clades; hover a segment to
                reveal its ancestor. The focused node expands into the chamber details card.
              </p>
              {focusRow && (
                <p className="font-mono text-xs text-primary/90">{formatLitDual(focusRow)}</p>
              )}
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">{headerExtra}</div>
        </div>
      </header>
      <div ref={liveRef} className="sr-only" aria-live="polite" aria-atomic="true" />
      <div className={cn("flex min-h-0 min-w-0 flex-1 flex-col")}>{children}</div>
    </div>
  )
}

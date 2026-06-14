"use client"

import Link from "next/link"
import { useEffect, useRef, type ReactNode } from "react"
import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import { formatDualCount } from "@/lib/taxonomy-mock"
import { buttonVariants } from "@/components/ui/button"
import { ArrowLeft } from "lucide-react"
import { cn } from "@/lib/utils"

export function FocusStackShell({
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
    liveRef.current.textContent = `${focusRow.scientific_name} — ${formatDualCount(
      focusRow.species_count_matrix,
      focusRow.species_count_ncbi,
    )}`
  }, [focusRow])

  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-4">
      <header className="min-w-0 shrink-0 border-b border-border pb-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div className="min-w-0 space-y-2">
            <Link
              href="/taxonomy/concepts"
              className={cn(
                buttonVariants({ variant: "ghost", size: "sm" }),
                "-ml-2 h-8 px-2",
              )}
            >
              <ArrowLeft className="mr-1 size-4" />
              Concepts
            </Link>
            <div>
              <h1 className="text-xl font-semibold tracking-tight">Taxonomy Focus Stack</h1>
              <p className="max-w-2xl text-sm text-muted-foreground">
                Ancestors on the left, taxon details in the center, children on the right. Arrow
                keys navigate children; Esc ascends to parent.
              </p>
              {focusRow && (
                <p className="mt-1 font-mono text-xs text-primary">
                  {formatDualCount(focusRow.species_count_matrix, focusRow.species_count_ncbi)}
                </p>
              )}
            </div>
          </div>
          <div className="flex flex-wrap items-center gap-2">{headerExtra}</div>
        </div>
      </header>
      <div ref={liveRef} className="sr-only" aria-live="polite" aria-atomic="true" />
      <div className="flex min-h-0 min-w-0 flex-1 flex-col">{children}</div>
    </div>
  )
}

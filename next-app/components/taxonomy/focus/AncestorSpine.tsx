"use client"

import { useMemo } from "react"
import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import { formatDualCount, pctCatalog } from "@/lib/taxonomy-mock"
import { getLeftSpineAncestors, truncateLeftSpine } from "@/lib/taxonomy/focus-nav"
import { SpineTab } from "./SpineTab"
import { TaxonName } from "../TaxonName"
import { cn } from "@/lib/utils"

export function AncestorSpine({
  focusTaxid,
  onJump,
  disabled,
  className,
}: {
  focusTaxid: number
  onJump: (taxid: number) => void
  disabled?: boolean
  className?: string
}) {
  const ancestors = useMemo(() => getLeftSpineAncestors(focusTaxid), [focusTaxid])
  const { visible, hasMore, rootTaxid } = useMemo(
    () => truncateLeftSpine(ancestors),
    [ancestors],
  )

  if (visible.length === 0 && !hasMore) {
    return (
      <div
        className={cn("flex w-full items-center justify-center text-[10px] text-muted-foreground/50", className)}
        aria-hidden
      >
        ·
      </div>
    )
  }

  return (
    <nav aria-label="Ancestor path" className={cn("flex flex-col gap-2", className)}>
      {hasMore && rootTaxid != null && (
        <button
          type="button"
          disabled={disabled}
          onClick={() => onJump(rootTaxid)}
          className="spine-tab rounded-lg border border-dashed border-border/50 py-2 text-[10px] text-muted-foreground hover:bg-secondary/60 disabled:opacity-50"
          title="Jump to root of visible path"
        >
          ↑ root
        </button>
      )}
      {visible.map((a: TaxonRollup) => (
        <SpineTab
          key={a.taxid}
          row={a}
          variant="ancestor"
          disabled={disabled}
          onClick={(e) => onJump(a.taxid)}
        />
      ))}
    </nav>
  )
}

export function MobileAncestorBar({
  focusTaxid,
  onJump,
  disabled,
  className,
}: {
  focusTaxid: number
  onJump: (taxid: number) => void
  disabled?: boolean
  className?: string
}) {
  const ancestors = useMemo(() => getLeftSpineAncestors(focusTaxid), [focusTaxid])
  const { visible, hasMore, rootTaxid } = useMemo(
    () => truncateLeftSpine(ancestors, 6),
    [ancestors],
  )

  if (visible.length === 0 && !hasMore) return null

  return (
    <nav
      aria-label="Ancestor path"
      className={cn("flex min-w-0 gap-1.5 overflow-x-auto overscroll-x-contain pb-1", className)}
    >
      {hasMore && rootTaxid != null && (
        <button
          type="button"
          disabled={disabled}
          onClick={() => onJump(rootTaxid)}
          className="spine-tab shrink-0 rounded-md border border-dashed border-border/50 px-2 py-1 text-[10px] text-muted-foreground"
        >
          ↑ root
        </button>
      )}
      {visible.map((a) => {
        const lit = pctCatalog(a)
        return (
          <button
            key={a.taxid}
            type="button"
            disabled={disabled}
            onClick={() => onJump(a.taxid)}
            title={`${a.scientific_name} — ${formatDualCount(a.species_count_matrix, a.species_count_ncbi)}`}
            className="spine-tab shrink-0 rounded-md border border-border/60 bg-card/40 px-2 py-1 text-[10px] text-muted-foreground hover:bg-secondary/80 disabled:opacity-50"
            style={{ opacity: 0.5 + lit * 0.5 }}
          >
            <TaxonName name={a.scientific_name.split(" ")[0] ?? a.scientific_name} />
          </button>
        )
      })}
    </nav>
  )
}

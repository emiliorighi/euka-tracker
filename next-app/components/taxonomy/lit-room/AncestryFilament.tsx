"use client"

import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import { getLeftSpineAncestors, truncateLeftSpine } from "@/lib/taxonomy/focus-nav"
import { litPct } from "./lit-room-utils"
import { LitScientificName } from "./LitScientificName"
import { cn } from "@/lib/utils"

export function AncestryFilament({
  focusTaxid,
  onJump,
  disabled,
  variant = "vertical",
  className,
}: {
  focusTaxid: number
  onJump: (taxid: number) => void
  disabled?: boolean
  variant?: "vertical" | "horizontal"
  className?: string
}) {
  const { visible, hasMore, rootTaxid } = truncateLeftSpine(getLeftSpineAncestors(focusTaxid))

  if (variant === "horizontal") {
    return (
      <nav
        className={cn("filament-bar flex min-w-0 gap-1 overflow-x-auto pb-1", className)}
        aria-label="Ancestry thread"
      >
        {hasMore && rootTaxid != null && (
          <button
            type="button"
            disabled={disabled}
            onClick={() => onJump(rootTaxid)}
            className="filament-node filament-node-more shrink-0 rounded-full px-2 py-1 text-[10px] text-muted-foreground hover:bg-secondary/60 disabled:opacity-50"
          >
            …
          </button>
        )}
        {visible.map((a) => (
          <FilamentNode key={a.taxid} row={a} disabled={disabled} onJump={() => onJump(a.taxid)} compact />
        ))}
      </nav>
    )
  }

  return (
    <nav className={cn("filament-column flex h-full min-h-0 flex-col items-center", className)} aria-label="Ancestry thread">
      <div className="filament-thread absolute inset-y-4 left-1/2 w-px -translate-x-1/2 bg-gradient-to-b from-transparent via-primary/40 to-transparent" aria-hidden />
      <div className="relative flex min-h-0 flex-1 flex-col items-center gap-3 overflow-y-auto py-2">
        {hasMore && rootTaxid != null && (
          <button
            type="button"
            disabled={disabled}
            onClick={() => onJump(rootTaxid)}
            className="filament-node filament-node-more z-[1] size-7 rounded-full border border-dashed border-primary/30 text-[10px] text-muted-foreground hover:border-primary/60 disabled:opacity-50"
            title="Jump toward root"
          >
            …
          </button>
        )}
        {visible.map((a, i) => (
          <FilamentNode
            key={a.taxid}
            row={a}
            disabled={disabled}
            onJump={() => onJump(a.taxid)}
            style={{ animationDelay: `${i * 50}ms` }}
          />
        ))}
      </div>
    </nav>
  )
}

function FilamentNode({
  row,
  onJump,
  disabled,
  compact,
  style,
}: {
  row: TaxonRollup
  onJump: () => void
  disabled?: boolean
  compact?: boolean
  style?: React.CSSProperties
}) {
  const lit = litPct(row)

  return (
    <button
      type="button"
      disabled={disabled}
      onClick={onJump}
      className={cn(
        "filament-node group relative z-[1] rounded-full border transition-all duration-300",
        compact
          ? "shrink-0 px-2 py-1 text-[10px]"
          : "size-9 shrink-0",
        lit > 0 ? "border-primary/40 bg-primary/10 hover:border-primary/70" : "border-white/10 bg-white/[0.03]",
        "hover:shadow-[0_0_16px_oklch(0.72_0.16_152/0.35)] disabled:opacity-50",
      )}
      style={{
        ...style,
        boxShadow: lit > 0 ? `0 0 ${6 + lit * 10}px oklch(0.72 0.16 152 / ${0.2 + lit * 0.35})` : undefined,
      }}
      title={row.scientific_name}
    >
      {compact ? (
        <LitScientificName name={row.scientific_name.split(" ")[0] ?? row.scientific_name} className="text-[10px]" />
      ) : (
        <span className="sr-only">{row.scientific_name}</span>
      )}
      {!compact && (
        <span
          className="absolute inset-1 rounded-full bg-primary/30 opacity-0 transition-opacity group-hover:opacity-100"
          aria-hidden
        />
      )}
    </button>
  )
}

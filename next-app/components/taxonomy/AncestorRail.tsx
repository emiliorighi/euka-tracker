"use client"

import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import { pctCatalog, pctCatalogLabel } from "@/lib/taxonomy-mock"
import { TaxonName } from "./TaxonName"
import { cn } from "@/lib/utils"

export function AncestorRail({
  ancestors,
  focusTaxid,
  spillTaxid,
  onSelect,
  className,
}: {
  ancestors: TaxonRollup[]
  focusTaxid: number
  spillTaxid?: number
  onSelect?: (taxid: number) => void
  className?: string
}) {
  return (
    <nav aria-label="Ancestor path" className={cn("flex flex-col gap-1", className)}>
      {ancestors.map((a) => {
        const active = a.taxid === focusTaxid
        const spill = spillTaxid === a.taxid
        const lit = pctCatalog(a)
        return (
          <button
            key={a.taxid}
            type="button"
            onClick={() => onSelect?.(a.taxid)}
            disabled={!onSelect || active}
            className={cn(
              "rounded-lg border px-3 py-2 text-left transition-colors",
              active
                ? "border-primary/40 bg-primary/10"
                : "border-border bg-card/50 hover:bg-secondary/80",
              spill && !active && "border-primary/25 bg-primary/5",
            )}
            style={
              spill && !active
                ? { boxShadow: `inset 0 0 12px oklch(0.72 0.16 152 / ${lit * 0.35})` }
                : undefined
            }
          >
            <TaxonName name={a.scientific_name} className="block text-sm" />
            <span className="text-xs text-muted-foreground">{pctCatalogLabel(a)} lit</span>
          </button>
        )
      })}
    </nav>
  )
}

export function AncestorThread({
  ancestors,
  className,
}: {
  ancestors: TaxonRollup[]
  className?: string
}) {
  return (
    <div className={cn("flex flex-wrap items-center gap-1 text-xs text-muted-foreground", className)}>
      {ancestors.map((a, i) => (
        <span key={a.taxid} className="flex items-center gap-1">
          {i > 0 && <span className="opacity-40">→</span>}
          <span className={i === ancestors.length - 1 ? "text-primary" : ""}>
            {a.scientific_name}
          </span>
        </span>
      ))}
    </div>
  )
}

export function OrbitalTrail({
  ancestors,
  focusTaxid,
  onSelect,
  className,
}: {
  ancestors: TaxonRollup[]
  focusTaxid: number
  onSelect?: (taxid: number) => void
  className?: string
}) {
  return (
    <nav
      aria-label="Orbital ancestor trail"
      className={cn("flex flex-wrap items-center justify-center gap-2", className)}
    >
      {ancestors.map((a, i) => {
        const active = a.taxid === focusTaxid
        const lit = pctCatalog(a)
        return (
          <button
            key={a.taxid}
            type="button"
            disabled={!onSelect || active}
            onClick={() => onSelect?.(a.taxid)}
            className={cn(
              "flex flex-col items-center gap-0.5 transition-opacity",
              !active && onSelect && "hover:opacity-100 opacity-70",
            )}
          >
            <span
              className={cn(
                "block size-2.5 rounded-full border",
                active ? "border-primary bg-primary" : "border-muted-foreground bg-secondary",
              )}
              style={!active ? { opacity: 0.4 + lit * 0.6 } : undefined}
            />
            {i === ancestors.length - 1 && (
              <span className="max-w-[72px] truncate text-[9px] text-primary">
                {a.scientific_name.split(" ")[0]}
              </span>
            )}
          </button>
        )
      })}
    </nav>
  )
}

import type { ReactNode } from "react"
import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import { LitScientificName } from "./LitScientificName"
import { isGhostRow, litPct } from "./lit-room-utils"
import { cn } from "@/lib/utils"

export function CladeCardShell({
  row,
  variant = "compact",
  badge,
  className,
  children,
}: {
  row: TaxonRollup
  variant?: "compact" | "hero"
  badge?: ReactNode
  className?: string
  children?: ReactNode
}) {
  const ghost = isGhostRow(row)
  const lit = litPct(row)

  return (
    <div
      className={cn(
        "clade-card-shell relative overflow-hidden rounded-xl border text-left",
        variant === "hero" ? "p-0" : "p-3 pt-4",
        ghost ? "border-dashed border-white/15 bg-white/[0.02]" : "border-white/10 bg-card/40",
        className,
      )}
      style={{
        boxShadow: ghost
          ? undefined
          : `inset 0 0 ${12 + lit * 20}px oklch(0.72 0.16 152 / ${0.06 + lit * 0.12})`,
      }}
    >
      <div
        className="clade-card-crest pointer-events-none absolute inset-x-3 top-0 h-6 rounded-b-[100%] border-x border-b border-primary/25 bg-primary/5"
        style={{ opacity: 0.3 + lit * 0.5 }}
        aria-hidden
      />
      {badge}
      {children ?? (
        <div className="relative space-y-1">
          <LitScientificName
            name={row.scientific_name}
            className={cn("line-clamp-2 leading-tight", variant === "hero" ? "text-base" : "text-xs")}
          />
          <span className="text-[10px] capitalize text-muted-foreground">{row.rank}</span>
          <CladeLitBar lit={lit} matrix={row.species_count_matrix} />
        </div>
      )}
    </div>
  )
}

export function CladeLitBar({ lit, matrix }: { lit: number; matrix: number }) {
  return (
    <div className="space-y-1 pt-1">
      <div className="h-1 overflow-hidden rounded-full bg-secondary/80">
        <div
          className="clade-lit-bar h-full rounded-full bg-primary transition-all duration-700"
          style={{
            width: `${Math.round(lit * 100)}%`,
            boxShadow: `0 0 8px oklch(0.72 0.16 152 / ${0.3 + lit * 0.4})`,
          }}
        />
      </div>
      <p className="font-mono text-[9px] tabular-nums text-muted-foreground">
        {matrix.toLocaleString()} lit · {(lit * 100).toFixed(1)}%
      </p>
    </div>
  )
}

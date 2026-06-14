import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import { litPct } from "./lit-room-utils"

export function CoverageArc({ row, glow }: { row: TaxonRollup; glow: number }) {
  const pct = litPct(row)
  const r = 36
  const c = 2 * Math.PI * r
  const dash = c * pct

  return (
    <div className="coverage-arc relative flex items-center gap-3">
      <svg
        viewBox="0 0 88 88"
        className="size-[4.5rem] shrink-0 -rotate-90"
        aria-hidden
      >
        <circle
          cx="44"
          cy="44"
          r={r}
          fill="none"
          stroke="oklch(1 0 0 / 8%)"
          strokeWidth="6"
        />
        <circle
          cx="44"
          cy="44"
          r={r}
          fill="none"
          stroke={`oklch(0.72 0.16 ${160 + row.depth_from_eukaryota * 2})`}
          strokeWidth="6"
          strokeLinecap="round"
          strokeDasharray={`${dash} ${c - dash}`}
          className="coverage-arc-fill transition-all duration-700"
          style={{ filter: `drop-shadow(0 0 ${8 + glow * 12}px oklch(0.72 0.16 152 / ${0.35 + glow * 0.4}))` }}
        />
      </svg>
      <div>
        <p className="text-[10px] uppercase tracking-widest text-muted-foreground">Catalog lit</p>
        <p className="font-mono text-2xl font-semibold tabular-nums text-primary">
          {(pct * 100).toFixed(1)}%
        </p>
        <p className="text-xs text-muted-foreground">
          {row.species_count_matrix.toLocaleString()} of{" "}
          {row.species_count_ncbi.toLocaleString()} species
        </p>
      </div>
    </div>
  )
}

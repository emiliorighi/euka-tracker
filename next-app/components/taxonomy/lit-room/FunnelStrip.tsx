import type { TaxonRollup } from "@/lib/taxonomy-mock/types"

const STAGES = [
  { key: "reads", label: "Reads", field: "species_with_reads" as const, color: "oklch(0.7 0.12 195)" },
  { key: "asm", label: "Assembly", field: "species_with_assembly" as const, color: "oklch(0.72 0.16 152)" },
  { key: "annot", label: "Annot", field: "species_with_annotation" as const, color: "oklch(0.66 0.13 245)" },
  { key: "triple", label: "Triple", field: "species_full_triple" as const, color: "oklch(0.78 0.15 75)" },
]

export function FunnelStrip({ row }: { row: TaxonRollup }) {
  const max = Math.max(row.species_count_ncbi, 1)

  return (
    <div className="funnel-strip space-y-2" aria-label="Genomic funnel">
      <p className="text-[10px] uppercase tracking-widest text-muted-foreground">Illumination funnel</p>
      <div className="grid grid-cols-4 gap-2">
        {STAGES.map((stage, i) => {
          const n = row[stage.field]
          const h = Math.max(8, Math.round((n / max) * 100))
          return (
            <div key={stage.key} className="funnel-strip-stage flex flex-col items-center gap-1">
              <div className="relative flex h-16 w-full items-end justify-center overflow-hidden rounded-md bg-secondary/40">
                <div
                  className="funnel-strip-bar w-full rounded-t-sm transition-all duration-700"
                  style={{
                    height: `${h}%`,
                    background: stage.color,
                    boxShadow: `0 0 12px ${stage.color}`,
                    animationDelay: `${i * 80}ms`,
                  }}
                />
              </div>
              <span className="text-[9px] uppercase text-muted-foreground">{stage.label}</span>
              <span className="font-mono text-[10px] tabular-nums">{n.toLocaleString()}</span>
            </div>
          )
        })}
      </div>
    </div>
  )
}

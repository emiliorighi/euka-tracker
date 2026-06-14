import type { TaxonRollup } from "@/lib/taxonomy-mock/types"

export function GhostVeil({ row }: { row: TaxonRollup }) {
  if (row.species_count_matrix > 0) return null

  return (
    <div className="ghost-veil relative overflow-hidden rounded-lg border border-dashed border-white/10 bg-white/[0.02] px-3 py-2">
      <div className="ghost-veil-fog pointer-events-none absolute inset-0" aria-hidden />
      <p className="relative text-sm text-muted-foreground">
        Unlit chamber —{" "}
        <span className="font-mono tabular-nums text-foreground/80">
          {row.species_count_ncbi.toLocaleString()}
        </span>{" "}
        NCBI species await catalog light.
      </p>
    </div>
  )
}

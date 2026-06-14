import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import { formatNumber } from "@/lib/taxonomy-mock"
import { MAX_TAXON_DEPTH, rankBreakdownLabel } from "@/lib/taxonomy/ranks"
import { DualCountBadge } from "./DualCountBadge"
import { RankPill } from "./GhostCladeHint"
import { TaxonName } from "./TaxonName"
import { cn } from "@/lib/utils"

function formatGenomeMb(n: number): string {
  if (n <= 0) return "—"
  return `${(n / 1e6).toFixed(1)} Mb`
}

export function DiveComputer({
  row,
  className,
}: {
  row: TaxonRollup
  className?: string
}) {
  const depthPct = Math.min(100, (row.depth_from_eukaryota / MAX_TAXON_DEPTH) * 100)
  const rankLabel = rankBreakdownLabel(row)

  return (
    <aside
      className={cn(
        "rounded-xl border border-border bg-card/80 p-4 backdrop-blur-sm",
        className,
      )}
    >
      <div className="mb-3 flex items-start justify-between gap-2">
        <div className="min-w-0">
          <TaxonName name={row.scientific_name} className="text-base" />
          <RankPill rank={row.rank} className="mt-1" />
        </div>
        <div className="shrink-0 text-right font-mono text-xs text-muted-foreground">
          depth {row.depth_from_eukaryota}
        </div>
      </div>
      <DualCountBadge matrix={row.species_count_matrix} ncbi={row.species_count_ncbi} />
      <div className="mt-3">
        <div className="mb-1 flex justify-between text-xs text-muted-foreground">
          <span>Descent depth</span>
          <span>{row.depth_from_eukaryota}/{MAX_TAXON_DEPTH}</span>
        </div>
        <div className="h-1.5 overflow-hidden rounded-full bg-secondary">
          <div
            className="h-full rounded-full bg-primary transition-all duration-300"
            style={{ width: `${depthPct}%` }}
          />
        </div>
      </div>
      {rankLabel && (
        <p className="mt-3 text-xs text-muted-foreground">{rankLabel}</p>
      )}
      <dl className="mt-4 grid grid-cols-2 gap-2 text-xs">
        <Stat label="With reads" value={row.species_with_reads} />
        <Stat label="With assembly" value={row.species_with_assembly} />
        <Stat label="With annotation" value={row.species_with_annotation} />
        <Stat label="Full triple" value={row.species_full_triple} />
        <Stat label="IUCN assessed" value={row.species_iucn_assessed} />
        <Stat label="Threatened" value={row.species_threatened} />
      </dl>
      {row.n_with_assembly > 0 && row.mean_genome_size > 0 && (
        <p className="mt-3 text-xs text-muted-foreground">
          Mean genome: {formatGenomeMb(row.mean_genome_size)}{" "}
          <span className="text-muted-foreground/70">(n={row.n_with_assembly})</span>
        </p>
      )}
    </aside>
  )
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="rounded-md bg-secondary/60 px-2 py-1.5">
      <dt className="text-muted-foreground">{label}</dt>
      <dd className="font-mono tabular-nums">{formatNumber(value)}</dd>
    </div>
  )
}

"use client"

import {
  Dna,
  FlaskConical,
  ShieldAlert,
  Layers,
  FileText,
  Activity,
} from "lucide-react"
import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import {
  formatDualCount,
  formatNumber,
  getAncestorsOf,
  pctCatalog,
  pctCatalogLabel,
  runCount,
} from "@/lib/taxonomy-mock"
import { getRankColor, getRankColorSolid } from "@/lib/taxonomy/rank-colors"
import { nextRank, rankBreakdownLabel, rankNodeCounts } from "@/lib/taxonomy/ranks"
import { TaxonName } from "@/components/taxonomy/TaxonName"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Progress } from "@/components/ui/progress"
import { AtlasStatCard } from "./AtlasStatCard"
import { cn } from "@/lib/utils"

function formatGenomeMb(n: number): string {
  if (n <= 0) return "—"
  if (n >= 1000) return `${(n / 1000).toFixed(1)} Gb`
  return `${n.toFixed(0)} Mb`
}

function MetricRow({ label, value, pct }: { label: string; value: string; pct: number }) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium tabular-nums">{value}</span>
      </div>
      <Progress value={pct} className="h-1" />
    </div>
  )
}

export function AtlasDetail({
  row,
  onSelectAncestor,
  className,
}: {
  row: TaxonRollup
  onSelectAncestor: (taxid: number) => void
  className?: string
}) {
  const ancestors = getAncestorsOf(row.taxid).filter((a) => a.taxid !== row.taxid)
  const lit = pctCatalog(row)
  const nr = nextRank(row.rank)
  const rankLabel = rankBreakdownLabel(row)
  const { total: nextTotal, withData: nextWithData } = nr ? rankNodeCounts(row, nr) : { total: 0, withData: 0 }

  const funnelSteps = [
    { label: "NCBI species", value: row.species_count_ncbi, color: "oklch(0.55 0.02 260)" },
    { label: "With reads", value: row.species_with_reads, color: "oklch(0.65 0.12 200)" },
    { label: "With assembly", value: row.species_with_assembly, color: "oklch(0.72 0.14 170)" },
    { label: "With annotation", value: row.species_with_annotation, color: "oklch(0.72 0.16 140)" },
    { label: "Full triple", value: row.species_full_triple, color: "oklch(0.72 0.16 120)" },
  ]
  const funnelMax = Math.max(row.species_count_ncbi, 1)

  const genomePct = row.mean_genome_size > 0 ? Math.min((row.mean_genome_size / 8e9) * 100, 100) : 0
  const gcPct = row.mean_gc_percent > 0 ? Math.min(row.mean_gc_percent, 100) : 0
  const buscoPct = row.mean_busco_complete > 0 ? Math.min(row.mean_busco_complete, 100) : 0

  return (
    <div className={cn("atlas-detail min-w-0 space-y-6", className)}>
      <header className="space-y-3 border-b border-border/60 pb-5">
        {ancestors.length > 0 && (
          <nav className="flex flex-wrap items-center gap-1 text-xs text-muted-foreground" aria-label="Breadcrumb">
            {ancestors.map((a, i) => (
              <span key={a.taxid} className="flex items-center gap-1">
                {i > 0 && <span aria-hidden>/</span>}
                <button
                  type="button"
                  onClick={() => onSelectAncestor(a.taxid)}
                  className="rounded px-1 hover:bg-secondary/60 hover:text-foreground"
                >
                  {a.scientific_name.split(" ")[0]}
                </button>
              </span>
            ))}
          </nav>
        )}

        <div className="space-y-2">
          <div className="flex flex-wrap items-center gap-2">
            <span
              className="rounded-md px-2 py-0.5 text-[10px] font-medium uppercase tracking-wider"
              style={{
                color: getRankColorSolid(row.rank),
                backgroundColor: getRankColor(row.rank, 0.12),
              }}
            >
              {row.rank}
            </span>
            <span className="font-mono text-xs text-muted-foreground">taxid {row.taxid}</span>
          </div>
          <h2
            data-atlas-detail-title
            className="text-balance text-2xl font-semibold tracking-tight md:text-3xl"
          >
            <TaxonName name={row.scientific_name} className="italic" />
          </h2>
          <p className="font-mono text-sm text-primary/90">{formatDualCount(row.species_count_matrix, row.species_count_ncbi)}</p>
          <p className="text-sm text-muted-foreground">{pctCatalogLabel(row)} catalog coverage</p>
        </div>
      </header>

      <section className="grid grid-cols-2 gap-3 lg:grid-cols-3 xl:grid-cols-6">
        <AtlasStatCard
          icon={Dna}
          label="Catalog species"
          value={formatNumber(row.species_count_matrix)}
          unit={`/ ${formatNumber(row.species_count_ncbi)}`}
          sublabel="Matrix / NCBI"
          accent
        />
        <AtlasStatCard
          icon={Layers}
          label="Coverage"
          value={pctCatalogLabel(row)}
          sublabel="NCBI species with data"
        />
        <AtlasStatCard
          icon={ShieldAlert}
          label="Threatened"
          value={row.species_threatened}
          unit={row.species_iucn_assessed > 0 ? `/ ${row.species_iucn_assessed}` : undefined}
          sublabel="IUCN assessed"
        />
        <AtlasStatCard
          icon={FlaskConical}
          label="Assemblies"
          value={formatNumber(row.sum_assembly_count)}
          sublabel={`${formatNumber(row.n_with_assembly)} species`}
        />
        <AtlasStatCard
          icon={FileText}
          label="Annotations"
          value={formatNumber(row.sum_annotation_count)}
          sublabel={`${formatNumber(row.n_with_annotation)} species`}
        />
        <AtlasStatCard
          icon={Activity}
          label="Read runs"
          value={formatNumber(runCount(row))}
          sublabel={`${formatNumber(row.species_with_reads)} species w/ reads`}
        />
      </section>

      <section className="grid gap-4 lg:grid-cols-3">
        <Card className="border-border/60 bg-card/50 lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">Data coverage funnel</CardTitle>
            <p className="text-xs text-muted-foreground">
              Species counts at each catalog tier under this clade
            </p>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex h-2.5 w-full overflow-hidden rounded-full bg-secondary/50">
              {funnelSteps.map((step) => (
                <div
                  key={step.label}
                  style={{
                    width: `${(step.value / funnelMax) * 100}%`,
                    backgroundColor: step.color,
                    minWidth: step.value > 0 ? "2px" : 0,
                  }}
                  title={`${step.label}: ${formatNumber(step.value)}`}
                />
              ))}
            </div>
            <div className="grid grid-cols-2 gap-x-4 gap-y-2 sm:grid-cols-3">
              {funnelSteps.map((step) => (
                <div key={step.label} className="flex items-center gap-2 text-xs">
                  <span
                    className="size-2 shrink-0 rounded-full"
                    style={{ backgroundColor: step.color }}
                  />
                  <span className="text-muted-foreground">{step.label}</span>
                  <span className="ml-auto font-medium tabular-nums">{formatNumber(step.value)}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card className="border-border/60 bg-card/50">
          <CardHeader>
            <CardTitle className="text-base">Genomic averages</CardTitle>
            <p className="text-xs text-muted-foreground">Mean assembly metrics</p>
          </CardHeader>
          <CardContent className="space-y-4">
            <MetricRow
              label="Genome size"
              value={formatGenomeMb(row.mean_genome_size / 1e6)}
              pct={genomePct}
            />
            <MetricRow label="GC content" value={`${row.mean_gc_percent.toFixed(1)}%`} pct={gcPct} />
            <MetricRow
              label="BUSCO complete"
              value={`${row.mean_busco_complete.toFixed(1)}%`}
              pct={buscoPct}
            />
          </CardContent>
        </Card>
      </section>

      {nr && nextTotal > 0 && (
        <Card className="border-border/60 bg-card/50">
          <CardHeader>
            <CardTitle className="text-base">Sub-clade breakdown</CardTitle>
            <p className="text-xs text-muted-foreground">
              {rankLabel ?? `${nextWithData}/${nextTotal} ${nr} nodes with catalog data`}
            </p>
          </CardHeader>
          <CardContent>
            <div className="flex items-center gap-3">
              <Progress value={(nextWithData / nextTotal) * 100} className="h-2 flex-1" />
              <span className="shrink-0 font-mono text-sm tabular-nums">
                {nextWithData}/{nextTotal}
              </span>
            </div>
          </CardContent>
        </Card>
      )}
    </div>
  )
}

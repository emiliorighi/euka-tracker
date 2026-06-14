"use client"

import Link from "next/link"
import {
  Dna,
  Globe2,
  ShieldAlert,
  FlaskConical,
  ArrowUpRight,
  Microscope,
  Layers,
} from "lucide-react"
import {
  SPECIES,
  getOverviewStats,
  iucnDistribution,
  getTaxonomyTree,
  formatGenomeSize,
  formatNumber,
} from "@/lib/biodiversity-data"
import { PageHeader } from "@/components/page-header"
import { StatCard } from "@/components/stat-card"
import { IucnBadge } from "@/components/iucn-badge"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Progress } from "@/components/ui/progress"

const stats = getOverviewStats()
const iucn = iucnDistribution()
const tree = getTaxonomyTree()

export default function DashboardPage() {
  const threatenedPct = Math.round((stats.threatened / stats.totalSpecies) * 100)
  const recentlySequenced = [...SPECIES]
    .sort((a, b) => b.sequencedYear - a.sequencedYear)
    .slice(0, 5)
  const mostSampled = [...SPECIES].sort((a, b) => b.sampleCount - a.sampleCount).slice(0, 5)

  return (
    <div className="space-y-8">
      <PageHeader
        eyebrow="Overview"
        title="Eukaryote Genomics Atlas"
        description="A consolidated view of genome assemblies, sampling effort, and conservation status across the eukaryotic tree of life."
      >
        <div className="flex flex-wrap gap-2">
          <Button
            variant="default"
            size="sm"
            render={
              <Link href="/taxonomy/atlas?view=scatter">
                Explore scatter
                <ArrowUpRight className="size-4" />
              </Link>
            }
          />
          <Button
            variant="outline"
            size="sm"
            render={
              <Link href="/species">
                Browse catalogue
                <ArrowUpRight className="size-4" />
              </Link>
            }
          />
        </div>
      </PageHeader>

      {/* Primary counts */}
      <section className="grid grid-cols-2 gap-4 lg:grid-cols-4">
        <StatCard
          icon={Dna}
          label="Species"
          value={formatNumber(stats.totalSpecies)}
          sublabel={`${stats.kingdoms} kingdoms represented`}
          accent
        />
        <StatCard
          icon={FlaskConical}
          label="Sequenced samples"
          value={formatNumber(stats.totalSamples)}
          sublabel={`${stats.completeGenomes} complete genomes`}
        />
        <StatCard
          icon={Globe2}
          label="Countries"
          value={stats.countries}
          sublabel="Sampling localities worldwide"
        />
        <StatCard
          icon={ShieldAlert}
          label="Threatened"
          value={stats.threatened}
          unit={`/ ${stats.totalSpecies}`}
          sublabel={`${threatenedPct}% on the IUCN Red List`}
        />
      </section>

      {/* Conservation + genomics averages */}
      <section className="grid gap-4 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader className="flex-row items-center justify-between">
            <div>
              <CardTitle>Conservation status</CardTitle>
              <p className="mt-1 text-sm text-muted-foreground">
                IUCN Red List distribution across catalogued species
              </p>
            </div>
            <Button
              variant="ghost"
              size="sm"
              className="text-muted-foreground"
              render={
                <Link href="/species">
                  Details
                  <ArrowUpRight className="size-4" />
                </Link>
              }
            />
          </CardHeader>
          <CardContent className="space-y-5">
            {/* Stacked proportional bar */}
            <div className="flex h-3 w-full overflow-hidden rounded-full">
              {iucn.map((d) => (
                <div
                  key={d.status}
                  style={{
                    width: `${(d.count / stats.totalSpecies) * 100}%`,
                    backgroundColor: d.color,
                  }}
                  title={`${d.label}: ${d.count}`}
                />
              ))}
            </div>
            <div className="grid grid-cols-2 gap-x-6 gap-y-3 sm:grid-cols-4">
              {iucn.map((d) => (
                <div key={d.status} className="flex items-center gap-2">
                  <span
                    className="size-2.5 shrink-0 rounded-full"
                    style={{ backgroundColor: d.color }}
                  />
                  <span className="font-mono text-xs text-muted-foreground">{d.status}</span>
                  <span className="ml-auto text-sm font-medium tabular-nums">{d.count}</span>
                </div>
              ))}
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Assembly averages</CardTitle>
            <p className="mt-1 text-sm text-muted-foreground">Mean metrics across all assemblies</p>
          </CardHeader>
          <CardContent className="space-y-5">
            <MetricRow
              label="Genome size"
              value={formatGenomeSize(stats.avgGenomeMb)}
              pct={Math.min((stats.avgGenomeMb / 8000) * 100, 100)}
            />
            <MetricRow label="GC content" value={`${stats.avgGc.toFixed(1)}%`} pct={stats.avgGc} />
            <MetricRow
              label="BUSCO completeness"
              value={`${stats.avgBusco.toFixed(1)}%`}
              pct={stats.avgBusco}
            />
          </CardContent>
        </Card>
      </section>

      {/* Kingdom breakdown */}
      <section className="grid gap-4 lg:grid-cols-3">
        {tree.map((k) => (
          <Card key={k.name}>
            <CardHeader className="flex-row items-center gap-3">
              <span
                className="flex size-9 items-center justify-center rounded-lg"
                style={{ backgroundColor: `color-mix(in oklch, ${k.color} 18%, transparent)` }}
              >
                <Layers className="size-4" style={{ color: k.color }} />
              </span>
              <div>
                <CardTitle className="text-base">{k.name}</CardTitle>
                <p className="text-xs text-muted-foreground">{k.count} species</p>
              </div>
            </CardHeader>
            <CardContent className="grid grid-cols-2 gap-4 text-sm">
              <Kv label="Avg genome" value={formatGenomeSize(k.avgGenomeMb)} />
              <Kv label="Avg GC" value={`${k.avgGc.toFixed(1)}%`} />
              <Kv label="Avg BUSCO" value={`${k.avgBusco.toFixed(0)}%`} />
              <Kv label="Threatened" value={`${k.threatened}/${k.count}`} />
            </CardContent>
          </Card>
        ))}
      </section>

      {/* Recent + most sampled */}
      <section className="grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader className="flex-row items-center gap-2">
            <Microscope className="size-4 text-primary" />
            <CardTitle className="text-base">Recently sequenced</CardTitle>
          </CardHeader>
          <CardContent className="divide-y divide-border">
            {recentlySequenced.map((s) => (
              <Link
                key={s.id}
                href={`/species?focus=${s.id}`}
                className="flex items-center gap-3 py-2.5 transition-colors hover:text-primary"
              >
                <span className="text-xs font-medium tabular-nums text-muted-foreground">
                  {s.sequencedYear}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium italic">{s.scientificName}</p>
                  <p className="truncate text-xs text-muted-foreground">{s.commonName}</p>
                </div>
                <IucnBadge status={s.iucn} />
              </Link>
            ))}
          </CardContent>
        </Card>

        <Card>
          <CardHeader className="flex-row items-center gap-2">
            <FlaskConical className="size-4 text-primary" />
            <CardTitle className="text-base">Most sampled</CardTitle>
          </CardHeader>
          <CardContent className="divide-y divide-border">
            {mostSampled.map((s) => (
              <Link
                key={s.id}
                href={`/species?focus=${s.id}`}
                className="flex items-center gap-3 py-2.5 transition-colors hover:text-primary"
              >
                <div className="min-w-0 flex-1">
                  <p className="truncate text-sm font-medium italic">{s.scientificName}</p>
                  <p className="truncate text-xs text-muted-foreground">{s.commonName}</p>
                </div>
                <span className="text-sm font-semibold tabular-nums">
                  {formatNumber(s.sampleCount)}
                </span>
                <span className="text-xs text-muted-foreground">samples</span>
              </Link>
            ))}
          </CardContent>
        </Card>
      </section>
    </div>
  )
}

function MetricRow({ label, value, pct }: { label: string; value: string; pct: number }) {
  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between text-sm">
        <span className="text-muted-foreground">{label}</span>
        <span className="font-medium tabular-nums">{value}</span>
      </div>
      <Progress value={pct} className="h-1.5" />
    </div>
  )
}

function Kv({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="font-medium tabular-nums">{value}</p>
    </div>
  )
}

"use client"

import { useState, useMemo } from "react"
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  ResponsiveContainer,
  Cell,
  RadialBarChart,
  RadialBar,
  PolarAngleAxis,
} from "recharts"
import { PageHeader } from "@/components/page-header"
import {
  getTaxonomyTree,
  type TaxonNode,
  formatGenomeSize,
  formatNumber,
} from "@/lib/biodiversity-data"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { ChevronRight, Home, Dna, Gauge, Boxes, ShieldAlert } from "lucide-react"

export default function TaxonomyPage() {
  const tree = useMemo(() => getTaxonomyTree(), [])
  // path holds the drill-down trail of selected node names
  const [path, setPath] = useState<string[]>([])

  // Resolve current level + selected node from the path
  const { levelNodes, selected, levelLabel } = useMemo(() => {
    let nodes = tree
    let sel: TaxonNode | null = null
    for (const name of path) {
      const found = nodes.find((n) => n.name === name)
      if (!found) break
      sel = found
      nodes = found.children ?? []
    }
    const rankLabel =
      path.length === 0 ? "Kingdoms" : path.length === 1 ? "Phyla" : "Classes"
    return { levelNodes: nodes, selected: sel, levelLabel: rankLabel }
  }, [tree, path])

  // What to show in the bar chart: children of the selected node, or the kingdom level
  const chartNodes = selected?.children?.length ? selected.children : levelNodes
  const canDrill = (node: TaxonNode) => (node.children?.length ?? 0) > 0

  const breadcrumb = ["All Eukaryotes", ...path]

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Taxonomy Explorer"
        description="Drill down from kingdom to class to compare genomic metadata averages across the tree of life."
      />

      {/* Breadcrumbs — progressive disclosure trail */}
      <nav aria-label="Taxonomy breadcrumb" className="flex flex-wrap items-center gap-1 text-sm">
        {breadcrumb.map((crumb, i) => {
          const isLast = i === breadcrumb.length - 1
          return (
            <span key={crumb} className="flex items-center gap-1">
              {i > 0 && <ChevronRight className="size-3.5 text-muted-foreground/50" />}
              <button
                onClick={() => setPath(path.slice(0, i))}
                disabled={isLast}
                className={`flex items-center gap-1 rounded-md px-2 py-1 transition-colors ${
                  isLast
                    ? "font-medium text-foreground"
                    : "text-muted-foreground hover:bg-secondary hover:text-foreground"
                }`}
              >
                {i === 0 && <Home className="size-3.5" />}
                {crumb}
              </button>
            </span>
          )
        })}
      </nav>

      <div className="grid gap-6 lg:grid-cols-5">
        {/* Bar chart of counts */}
        <Card className="border-border bg-card lg:col-span-3">
          <CardHeader>
            <CardTitle className="text-base">
              Species count by {levelLabel.toLowerCase()}
            </CardTitle>
            <p className="text-sm text-muted-foreground">
              {canDrill(chartNodes[0] ?? ({} as TaxonNode))
                ? "Select a bar to drill deeper into the taxonomy."
                : "Lowest level reached — showing class composition."}
            </p>
          </CardHeader>
          <CardContent>
            <ResponsiveContainer width="100%" height={Math.max(240, chartNodes.length * 46)}>
              <BarChart
                data={chartNodes}
                layout="vertical"
                margin={{ left: 8, right: 24, top: 0, bottom: 0 }}
              >
                <CartesianGrid horizontal={false} stroke="var(--color-border)" />
                <XAxis
                  type="number"
                  stroke="var(--color-muted-foreground)"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <YAxis
                  type="category"
                  dataKey="name"
                  width={120}
                  stroke="var(--color-muted-foreground)"
                  fontSize={12}
                  tickLine={false}
                  axisLine={false}
                />
                <Bar
                  dataKey="count"
                  radius={[0, 4, 4, 0]}
                  cursor="pointer"
                  onClick={(d: { name?: string }) => {
                    const node = chartNodes.find((n) => n.name === d.name)
                    if (node && canDrill(node)) setPath([...path, node.name])
                  }}
                >
                  {chartNodes.map((n) => (
                    <Cell key={n.name} fill={n.color} fillOpacity={0.85} />
                  ))}
                </Bar>
              </BarChart>
            </ResponsiveContainer>
          </CardContent>
        </Card>

        {/* Metadata averages for the selected node (or whole tree) */}
        <Card className="border-border bg-card lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-base">
              {selected ? selected.name : "All Eukaryotes"}
            </CardTitle>
            <p className="text-sm capitalize text-muted-foreground">
              {selected ? `${selected.rank} averages` : "Dataset averages"}
            </p>
          </CardHeader>
          <CardContent className="flex flex-col gap-4">
            {(() => {
              const n =
                selected ??
                ({
                  count: chartNodes.reduce((a, c) => a + c.count, 0),
                  threatened: chartNodes.reduce((a, c) => a + c.threatened, 0),
                  totalSamples: chartNodes.reduce((a, c) => a + c.totalSamples, 0),
                  avgGenomeMb:
                    chartNodes.reduce((a, c) => a + c.avgGenomeMb * c.count, 0) /
                    chartNodes.reduce((a, c) => a + c.count, 0),
                  avgGc:
                    chartNodes.reduce((a, c) => a + c.avgGc * c.count, 0) /
                    chartNodes.reduce((a, c) => a + c.count, 0),
                  avgBusco:
                    chartNodes.reduce((a, c) => a + c.avgBusco * c.count, 0) /
                    chartNodes.reduce((a, c) => a + c.count, 0),
                  avgChromosomes:
                    chartNodes.reduce((a, c) => a + c.avgChromosomes * c.count, 0) /
                    chartNodes.reduce((a, c) => a + c.count, 0),
                } as TaxonNode)
              const threatPct = n.count ? Math.round((n.threatened / n.count) * 100) : 0
              return (
                <>
                  <div className="grid grid-cols-2 gap-3">
                    <Metric icon={Dna} label="Avg genome" value={formatGenomeSize(n.avgGenomeMb)} />
                    <Metric icon={Gauge} label="Avg GC" value={`${n.avgGc.toFixed(1)}%`} />
                    <Metric icon={Gauge} label="Avg BUSCO" value={`${n.avgBusco.toFixed(1)}%`} />
                    <Metric
                      icon={Boxes}
                      label="Avg chromosomes"
                      value={n.avgChromosomes.toFixed(0)}
                    />
                  </div>

                  {/* Threatened radial gauge */}
                  <div className="flex items-center gap-4 rounded-lg border border-border bg-secondary/40 p-4">
                    <div className="relative size-24 shrink-0">
                      <RadialBarChart
                        width={96}
                        height={96}
                        innerRadius="70%"
                        outerRadius="100%"
                        data={[{ value: threatPct }]}
                        startAngle={90}
                        endAngle={-270}
                      >
                        <PolarAngleAxis type="number" domain={[0, 100]} tick={false} />
                        <RadialBar
                          dataKey="value"
                          cornerRadius={8}
                          fill="var(--color-destructive)"
                          background={{ fill: "var(--color-muted)" }}
                        />
                      </RadialBarChart>
                      <div className="absolute inset-0 flex items-center justify-center">
                        <span className="text-lg font-semibold tabular-nums">{threatPct}%</span>
                      </div>
                    </div>
                    <div className="text-sm">
                      <p className="flex items-center gap-1.5 font-medium">
                        <ShieldAlert className="size-4 text-destructive" /> Threatened
                      </p>
                      <p className="mt-1 text-muted-foreground">
                        {formatNumber(n.threatened)} of {formatNumber(n.count)} species are listed
                        in a threatened IUCN category.
                      </p>
                    </div>
                  </div>

                  <div className="flex items-center justify-between rounded-lg border border-border bg-secondary/40 px-4 py-3 text-sm">
                    <span className="text-muted-foreground">Total samples sequenced</span>
                    <span className="font-semibold tabular-nums">
                      {formatNumber(n.totalSamples)}
                    </span>
                  </div>
                </>
              )
            })()}
          </CardContent>
        </Card>
      </div>
    </div>
  )
}

function Metric({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof Dna
  label: string
  value: string
}) {
  return (
    <div className="rounded-lg border border-border bg-secondary/40 p-3">
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Icon className="size-3.5" />
        {label}
      </div>
      <p className="mt-1 text-base font-semibold tabular-nums">{value}</p>
    </div>
  )
}

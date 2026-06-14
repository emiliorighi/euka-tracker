import Link from "next/link"
import {
  getEukaryotaRow,
  getMammaliaRow,
  formatDualCount,
  pctCatalogLabel,
} from "@/lib/taxonomy-mock"
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { ArrowRight } from "lucide-react"

const CONCEPTS = [
  {
    href: "/taxonomy/atlas",
    title: "Taxonomy Atlas",
    pitch: "Full-bleed explorer — rank-colored hierarchy tree drives a live clade dashboard and species cards.",
    stat: () => "Tree · dashboard · species",
  },
  {
    href: "/taxonomy/lit-tree",
    title: "The Lit Tree",
    pitch: "Vertical collapsed-card tree — depth lines reveal ancestors on hover; focus expands into chamber details.",
    stat: () => "Tree · collapse · segment hover",
  },
  {
    href: "/taxonomy/lit-room",
    title: "The Lit Room",
    pitch: "Chamber metaphor — doorways drill deeper, floor tiles lift species detail in place.",
    stat: () => "Glow · fog · tile lift",
  },
  {
    href: "/taxonomy/focus",
    title: "Focus Stack",
    pitch: "Horizontal 3-column drill — ancestors left, taxon details center, child cards right.",
    stat: () => "Past · now · next",
  },
  {
    href: "/taxonomy/concepts/descent",
    title: "The Descent",
    pitch: "Vertical horizon rings — descend through clades with bioluminescent catalog coverage.",
    stat: () => {
      const e = getEukaryotaRow()
      return `${pctCatalogLabel(e)} of eukaryotes lit`
    },
  },
  {
    href: "/taxonomy/concepts/biolume",
    title: "Biolume Map",
    pitch: "Organic packed cells — NCBI area, catalog brightness, conservation veins.",
    stat: () => "21 kingdom-level cells",
  },
  {
    href: "/taxonomy/concepts/constellation",
    title: "Rank Constellation",
    pitch: "Mammalia orders as stars — swap lenses to change the telescope filter.",
    stat: () => "27 orders under Mammalia",
  },
  {
    href: "/taxonomy/concepts/funnel",
    title: "Funnel Cathedral",
    pitch: "Stained-glass genomic funnel — reads → assembly → annotation → triple.",
    stat: () => {
      const m = getMammaliaRow()
      return formatDualCount(m.species_count_matrix, m.species_count_ncbi)
    },
  },
  {
    href: "/taxonomy/concepts/specimen-stream",
    title: "Specimen Stream",
    pitch: "Horizontal museum drawer — species cards with data-tier glyphs.",
    stat: () => "40 species · Trichosanthes",
  },
  {
    href: "/taxonomy/concepts/symbiosis",
    title: "Compare as Symbiosis",
    pitch: "Pin two clades — overlapping rings, funnel diff, rank breakdown.",
    stat: () => "Mammalia vs Metazoa",
  },
] as const

const LEGEND = [
  { label: "Dark", desc: "NCBI biodiversity" },
  { label: "Biolume", desc: "Catalog coverage" },
  { label: "Amber", desc: "Conservation risk" },
] as const

export default function TaxonomyConceptsHubPage() {
  const euk = getEukaryotaRow()

  return (
    <div className="mx-auto flex min-w-0 w-full max-w-5xl flex-col gap-8">
      <header className="min-w-0 space-y-3">
        <p className="text-xs font-medium uppercase tracking-widest text-primary">UX prototypes</p>
        <h1 className="text-2xl font-semibold tracking-tight">Taxonomy concepts</h1>
        <p className="max-w-2xl text-sm text-muted-foreground">
          A bioluminescent descent through the tree of life — each clade shows how much of nature
          exists in the dark, and how much we have illuminated in the catalog. Powered by{" "}
          <code className="rounded bg-secondary px-1 text-xs">06_taxon_rollups.tsv</code>.
        </p>
        <p className="font-mono text-sm text-muted-foreground">
          Eukaryota: {formatDualCount(euk.species_count_matrix, euk.species_count_ncbi)}
        </p>
        <div className="flex flex-wrap gap-2">
          {LEGEND.map((item) => (
            <span
              key={item.label}
              className="rounded-full border border-border bg-card/60 px-3 py-1 text-xs text-muted-foreground"
            >
              <span className="font-medium text-foreground">{item.label}</span> — {item.desc}
            </span>
          ))}
        </div>
      </header>

      <div className="grid min-w-0 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {CONCEPTS.map((c) => (
          <Card key={c.href} className="min-w-0 border-border bg-card/80 transition-colors hover:border-primary/30">
            <CardHeader className="pb-2">
              <CardTitle className="text-base">{c.title}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              <p className="text-sm text-muted-foreground">{c.pitch}</p>
              <p className="font-mono text-xs text-primary">{c.stat()}</p>
              <Button variant="secondary" size="sm" asChild className="w-full">
                <Link href={c.href}>
                  Open demo
                  <ArrowRight className="ml-1 size-4" />
                </Link>
              </Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}

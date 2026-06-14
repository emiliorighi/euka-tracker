"use client"

import { Suspense } from "react"
import { EUKARYOTA_TAXID } from "@/lib/atlas-taxonomy"
import { AtlasTree } from "@/components/taxonomy/atlas/AtlasTree"
import { AtlasScatterPanel } from "@/components/taxonomy/atlas/AtlasScatterPanel"
import { useAtlasTree } from "@/hooks/useAtlasTree"
import "@/components/taxonomy/atlas/atlas.css"

function AtlasPageContent() {
  const { selectedTaxid, isExpanded, select } = useAtlasTree(EUKARYOTA_TAXID)

  return (
    <div className="relative h-full min-h-0 w-full overflow-hidden">
      <AtlasScatterPanel selectedTaxid={selectedTaxid} className="absolute inset-0" />

      <aside
        className="atlas-tree-column atlas-column absolute left-4 top-4 z-30 flex w-[min(24rem,42vw)] max-h-[calc(100%-2rem)] flex-col overflow-hidden rounded-xl border border-white/10 bg-background/70 p-4 shadow-2xl backdrop-blur-md md:p-5"
        aria-label="Taxonomy tree"
      >
        <AtlasTree
          className="flex-1"
          selectedTaxid={selectedTaxid}
          isExpanded={isExpanded}
          onSelect={select}
        />
      </aside>
    </div>
  )
}

export default function TaxonomyAtlasPage() {
  return (
    <Suspense
      fallback={
        <div className="flex h-full items-center justify-center text-sm text-muted-foreground">
          Loading atlas…
        </div>
      }
    >
      <AtlasPageContent />
    </Suspense>
  )
}

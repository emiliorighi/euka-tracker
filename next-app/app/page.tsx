"use client"

import dynamic from "next/dynamic"
import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { Map } from "lucide-react"
import { ExploreLegendStrip } from "@/components/explore/ExploreLegendStrip"
import { ExploreTopBar } from "@/components/explore/ExploreTopBar"
import { SpeciesDetailSheet } from "@/components/species-detail-sheet"
import { Button } from "@/components/ui/button"
import {
  buildScatterEncoding,
  cladeBackgroundOptions,
  scatterFilterKey,
  scatterTaxonKey,
} from "@/lib/scatter/encoding"
import type { IucnSpeciesDatum } from "@/lib/iucn/types"
import {
  getRollupStats,
  legendFilterCount,
  type SelectedTaxon,
  useIucnTreeStore,
} from "@/lib/iucn/tree-store"

/** Load scatter on demand in dev to avoid Turbopack RAM spikes; always load in production preview. */
const AUTO_LOAD_SCATTER = process.env.NODE_ENV !== "development"

const TaxonTreeSheet = dynamic(
  () =>
    import("@/components/explore/TaxonTreeSheet").then((mod) => mod.TaxonTreeSheet),
  { ssr: false },
)

const SpeciesScatterPlot = dynamic(
  () =>
    import("@/components/scatter/SpeciesScatterPlot").then(
      (mod) => mod.SpeciesScatterPlot,
    ),
  {
    ssr: false,
    loading: () => (
      <div className="flex h-full items-center justify-center bg-[#0a0a0a] text-sm text-muted-foreground">
        Loading scatter libraries…
      </div>
    ),
  },
)

export default function ExplorePage() {
  const [drawerOpen, setDrawerOpen] = useState(false)
  const [scatterActive, setScatterActive] = useState(false)
  const [selectedTaxon, setSelectedTaxon] = useState<SelectedTaxon | null>(null)
  const [detailSpecies, setDetailSpecies] = useState<IucnSpeciesDatum | null>(null)
  const [detailOpen, setDetailOpen] = useState(false)
  const [iucnFilter, setIucnFilter] = useState<string | null>(null)
  const [dataFilter, setDataFilter] = useState<string | null>(null)
  const scatterActivatedRef = useRef(false)

  const index = useIucnTreeStore((s) => s.index)
  const loadRollups = useIucnTreeStore((s) => s.load)
  const rollupStatus = useIucnTreeStore((s) => s.status)

  useEffect(() => {
    if (rollupStatus === "idle") void loadRollups()
  }, [rollupStatus, loadRollups])

  useEffect(() => {
    if (!AUTO_LOAD_SCATTER) return
    if (rollupStatus !== "ready") return
    if (scatterActivatedRef.current) return

    let cancelled = false
    const activate = () => {
      if (cancelled || scatterActivatedRef.current) return
      scatterActivatedRef.current = true
      setScatterActive(true)
    }

    if (typeof requestIdleCallback !== "undefined") {
      const id = requestIdleCallback(activate, { timeout: 2000 })
      return () => {
        cancelled = true
        cancelIdleCallback(id)
      }
    }

    activate()
    return () => {
      cancelled = true
    }
  }, [rollupStatus])

  useEffect(() => {
    const stats = getRollupStats(index, selectedTaxon)
    if (!stats) return

    setIucnFilter((prev) => {
      if (!prev) return prev
      return legendFilterCount(stats, "iucn", prev) <= 0 ? null : prev
    })
    setDataFilter((prev) => {
      if (!prev) return prev
      return legendFilterCount(stats, "pipeline", prev) <= 0 ? null : prev
    })
  }, [index, selectedTaxon])

  const selectionKey = selectedTaxon?.taxonKey ?? null

  const encoding = useMemo(
    () =>
      buildScatterEncoding({
        rank: selectedTaxon?.rank,
        taxonName: selectedTaxon?.taxonName,
        selectionKey,
        iucnFilter,
        dataFilter,
      }),
    [selectedTaxon, selectionKey, iucnFilter, dataFilter],
  )

  const filterKey = useMemo(
    () => scatterFilterKey(iucnFilter, dataFilter),
    [iucnFilter, dataFilter],
  )

  const taxonEncodingKey = useMemo(
    () =>
      scatterTaxonKey({
        rank: selectedTaxon?.rank,
        taxonName: selectedTaxon?.taxonName,
        selectionKey,
      }),
    [selectedTaxon, selectionKey],
  )

  const backgroundOptions = useMemo(
    () => cladeBackgroundOptions(selectedTaxon?.rank, selectedTaxon?.taxonName),
    [selectedTaxon],
  )

  const handleSelectTaxon = useCallback((taxon: SelectedTaxon | null) => {
    setSelectedTaxon(taxon)
  }, [])

  const handleSpeciesClick = useCallback((datum: IucnSpeciesDatum) => {
    setDetailSpecies(datum)
    setDetailOpen(true)
  }, [])

  return (
    <div className="flex h-[100dvh] min-h-0 flex-col overflow-hidden">
      <ExploreTopBar
        selectedTaxon={selectedTaxon}
        drawerOpen={drawerOpen}
        dataFilter={dataFilter}
        onBrowseToggle={() => setDrawerOpen((open) => !open)}
        onSelectTaxon={handleSelectTaxon}
        onDataFilterChange={setDataFilter}
      />

      <div className="relative min-h-0 flex-1">
        {scatterActive ? (
          <>
            <SpeciesScatterPlot
              encoding={encoding}
              filterKey={filterKey}
              taxonEncodingKey={taxonEncodingKey}
              backgroundOptions={backgroundOptions}
              selectedRank={selectedTaxon?.rank}
              selectedTaxonName={selectedTaxon?.taxonName}
              selectionKey={selectionKey}
              onSpeciesClick={handleSpeciesClick}
            />
            <ExploreLegendStrip
              iucnFilter={iucnFilter}
              selectedTaxon={selectedTaxon}
              onFilterChange={setIucnFilter}
            />
            <TaxonTreeSheet
              open={drawerOpen}
              onOpenChange={setDrawerOpen}
              selectedTaxon={selectedTaxon}
              onSelectTaxon={handleSelectTaxon}
            />
            <SpeciesDetailSheet
              species={detailSpecies}
              open={detailOpen}
              onOpenChange={setDetailOpen}
            />
          </>
        ) : (
          <div className="flex h-full flex-col items-center justify-center gap-4 bg-[#0a0a0a] p-6 text-center">
            <Map className="size-10 text-muted-foreground" />
            <div className="max-w-sm space-y-2">
              <p className="text-sm font-medium text-foreground">Scatter map not loaded</p>
              <p className="text-xs leading-relaxed text-muted-foreground">
                The map uses WebGL (deepscatter). In dev mode it is not loaded
                automatically because compiling those libraries can use several GB of RAM.
                Scatter data loads from quadfeather tiles via{" "}
                <code className="text-[11px]">/data/manifest.json</code> (172k rows, LOD on zoom).
              </p>
            </div>
            <Button onClick={() => setScatterActive(true)}>Load scatter map</Button>
          </div>
        )}
      </div>
    </div>
  )
}

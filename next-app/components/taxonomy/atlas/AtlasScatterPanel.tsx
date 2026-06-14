"use client"

import { useMemo, useState } from "react"
import dynamic from "next/dynamic"
import {
  cladeBackgroundOptions,
  IUCN_LABELS,
  IUCN_COLOR_RANGE,
  isCladeHighlightActive,
} from "@/lib/scatter/encoding"
import {
  buildLayoutEncoding,
  layoutEncodingKey,
  SCATTER_LAYOUT_OPTIONS,
  tileUrlForLayout,
  type ScatterLayoutId,
} from "@/lib/scatter/layouts"
import { getAtlasRowById } from "@/lib/atlas-taxonomy"
import { cn } from "@/lib/utils"

const SpeciesScatterPlot = dynamic(
  () =>
    import("@/components/scatter/SpeciesScatterPlot").then(
      (m) => m.SpeciesScatterPlot,
    ),
  {
    ssr: false,
    loading: () => (
      <div className="h-full w-full animate-pulse bg-muted/30" />
    ),
  },
)

function LegendSwatch({ color, label }: { color: string; label: string }) {
  return (
    <div className="flex items-center gap-2 text-[10px] text-muted-foreground">
      <span
        className="size-2 shrink-0 rounded-full"
        style={{ backgroundColor: color }}
        aria-hidden
      />
      <span>{label}</span>
    </div>
  )
}

export function AtlasScatterPanel({
  selectedTaxid,
  className,
}: {
  selectedTaxid: number
  className?: string
}) {
  const [layout, setLayout] = useState<ScatterLayoutId>("landscape")
  const selectedRow = useMemo(
    () => getAtlasRowById(selectedTaxid),
    [selectedTaxid],
  )
  const depthFromEukaryota = selectedRow?.depth_from_eukaryota ?? 0

  const sourceUrl = useMemo(() => tileUrlForLayout(layout), [layout])
  const encoding = useMemo(
    () => buildLayoutEncoding(layout, selectedTaxid, depthFromEukaryota),
    [layout, selectedTaxid, depthFromEukaryota],
  )
  const encodingKey = useMemo(
    () => layoutEncodingKey(layout, selectedTaxid, depthFromEukaryota),
    [layout, selectedTaxid, depthFromEukaryota],
  )
  const backgroundOptions = useMemo(
    () => cladeBackgroundOptions(selectedTaxid, depthFromEukaryota),
    [selectedTaxid, depthFromEukaryota],
  )
  const highlightActive = isCladeHighlightActive(
    selectedTaxid,
    depthFromEukaryota,
  )
  const activeLayout = SCATTER_LAYOUT_OPTIONS.find((opt) => opt.id === layout)
  const focusKey = useMemo(
    () => `${layout}|${selectedTaxid}|d${depthFromEukaryota}`,
    [layout, selectedTaxid, depthFromEukaryota],
  )

  return (
    <section
      className={cn("atlas-scatter-panel relative min-h-0 flex-1", className)}
      aria-label="Eukaryote study-gap scatter"
    >
      <div className="absolute inset-0 min-h-0">
        <SpeciesScatterPlot
          sourceUrl={sourceUrl}
          encoding={encoding}
          encodingKey={encodingKey}
          backgroundOptions={backgroundOptions}
          focusTaxid={selectedTaxid}
          focusDepth={depthFromEukaryota}
          focusKey={focusKey}
          layout={layout}
        />
        <div className="pointer-events-none absolute right-4 top-4 z-20 flex flex-col items-end gap-2">
          <div className="pointer-events-auto flex max-w-[calc(100vw-2rem)] flex-wrap justify-end gap-1 rounded-lg border border-white/10 bg-background/75 p-1 backdrop-blur-md">
            {SCATTER_LAYOUT_OPTIONS.map((opt) => (
              <button
                key={opt.id}
                type="button"
                onClick={() => setLayout(opt.id)}
                className={cn(
                  "rounded-md px-2 py-1 text-[10px] font-medium transition-colors",
                  layout === opt.id
                    ? "bg-primary text-primary-foreground"
                    : "text-muted-foreground hover:bg-muted/60 hover:text-foreground",
                )}
                aria-pressed={layout === opt.id}
                title={opt.description}
              >
                {opt.label}
              </button>
            ))}
          </div>
          {highlightActive && selectedRow ? (
            <div className="max-w-[14rem] rounded-lg border border-primary/30 bg-background/80 px-2.5 py-1.5 backdrop-blur-md">
              <p className="text-[9px] font-medium uppercase tracking-wider text-muted-foreground">
                Highlighting
              </p>
              <p className="truncate text-xs font-medium text-foreground">
                {selectedRow.scientific_name}
              </p>
              <p className="text-[10px] capitalize text-muted-foreground">
                {selectedRow.rank}
              </p>
            </div>
          ) : null}
        </div>
        <div className="pointer-events-none absolute bottom-4 right-4 z-20 flex flex-col items-end gap-2">
          {activeLayout ? (
            <div className="max-w-[12rem] rounded-lg border border-white/10 bg-background/70 px-2.5 py-1.5 backdrop-blur-md">
              <p className="text-[9px] font-medium uppercase tracking-wider text-muted-foreground">
                View
              </p>
              <p className="text-[10px] text-foreground">{activeLayout.description}</p>
            </div>
          ) : null}
          <div className="max-w-[11rem] rounded-lg border border-white/10 bg-background/70 p-2.5 backdrop-blur-md">
            <p className="mb-1.5 text-[9px] font-medium uppercase tracking-wider text-muted-foreground">
              IUCN status
            </p>
            <div className="max-h-36 space-y-1 overflow-y-auto">
              {Object.entries(IUCN_LABELS).map(([code, label]) => (
                <LegendSwatch
                  key={code}
                  color={IUCN_COLOR_RANGE[Number(code)] ?? "#334155"}
                  label={label}
                />
              ))}
            </div>
          </div>
        </div>
      </div>
    </section>
  )
}

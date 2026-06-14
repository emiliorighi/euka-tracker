"use client"

import { useState, useMemo } from "react"
import {
  ComposableMap,
  Geographies,
  Geography,
  Marker,
  ZoomableGroup,
} from "react-simple-maps"
import { PageHeader } from "@/components/page-header"
import { SpeciesDetailSheet } from "@/components/species-detail-sheet"
import { IucnBadge } from "@/components/iucn-badge"
import {
  species as allSpecies,
  type Species,
  type IucnStatus,
  IUCN_META,
  IUCN_ORDER,
  formatNumber,
} from "@/lib/biodiversity-data"
import { Card } from "@/components/ui/card"
import { Button } from "@/components/ui/button"
import { Plus, Minus, RotateCcw } from "lucide-react"

const GEO_URL =
  "https://cdn.jsdelivr.net/npm/world-atlas@2/countries-110m.json"

export default function MapPage() {
  const [selected, setSelected] = useState<Species | null>(null)
  const [open, setOpen] = useState(false)
  const [active, setActive] = useState<IucnStatus | null>(null)
  const [hovered, setHovered] = useState<Species | null>(null)
  const [zoom, setZoom] = useState(1)
  const [center, setCenter] = useState<[number, number]>([15, 20])

  const visible = useMemo(
    () => (active ? allSpecies.filter((s) => s.iucn === active) : allSpecies),
    [active],
  )

  function openSpecies(s: Species) {
    setSelected(s)
    setOpen(true)
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Sampling Map"
        description="Geographic distribution of sequenced Eukaryote specimens. Markers are colored by IUCN conservation status."
      />

      {/* Filter legend — progressive disclosure: click to focus a status */}
      <div className="flex flex-wrap items-center gap-2">
        <button
          onClick={() => setActive(null)}
          className={`rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
            active === null
              ? "border-primary bg-primary/15 text-primary"
              : "border-border text-muted-foreground hover:bg-secondary"
          }`}
        >
          All specimens ({formatNumber(allSpecies.length)})
        </button>
        {IUCN_ORDER.map((status) => {
          const count = allSpecies.filter((s) => s.iucn === status).length
          const isActive = active === status
          return (
            <button
              key={status}
              onClick={() => setActive(isActive ? null : status)}
              className={`flex items-center gap-1.5 rounded-full border px-3 py-1 text-xs font-medium transition-colors ${
                isActive
                  ? "border-primary bg-primary/15 text-foreground"
                  : "border-border text-muted-foreground hover:bg-secondary"
              }`}
            >
              <span
                className="size-2 rounded-full"
                style={{ backgroundColor: IUCN_META[status].color }}
              />
              {IUCN_META[status].label} ({count})
            </button>
          )
        })}
      </div>

      <Card className="relative overflow-hidden border-border bg-card p-0">
        {/* Zoom controls */}
        <div className="absolute right-3 top-3 z-10 flex flex-col gap-1">
          <Button
            size="icon"
            variant="secondary"
            className="size-8"
            onClick={() => setZoom((z) => Math.min(z * 1.5, 8))}
            aria-label="Zoom in"
          >
            <Plus className="size-4" />
          </Button>
          <Button
            size="icon"
            variant="secondary"
            className="size-8"
            onClick={() => setZoom((z) => Math.max(z / 1.5, 1))}
            aria-label="Zoom out"
          >
            <Minus className="size-4" />
          </Button>
          <Button
            size="icon"
            variant="secondary"
            className="size-8"
            onClick={() => {
              setZoom(1)
              setCenter([15, 20])
            }}
            aria-label="Reset view"
          >
            <RotateCcw className="size-4" />
          </Button>
        </div>

        {/* Hover tooltip */}
        {hovered && (
          <div className="pointer-events-none absolute left-3 top-3 z-10 max-w-xs rounded-lg border border-border bg-popover/95 p-3 text-popover-foreground shadow-lg backdrop-blur">
            <div className="flex items-center gap-2">
              <IucnBadge status={hovered.iucn} />
              <span className="text-xs text-muted-foreground">{hovered.country}</span>
            </div>
            <p className="mt-1 text-sm font-medium italic">{hovered.scientificName}</p>
            <p className="text-xs text-muted-foreground">{hovered.commonName}</p>
          </div>
        )}

        <div className="aspect-[16/10] w-full">
          <ComposableMap
            projection="geoEqualEarth"
            projectionConfig={{ scale: 165 }}
            style={{ width: "100%", height: "100%" }}
          >
            <ZoomableGroup
              zoom={zoom}
              center={center}
              onMoveEnd={({ coordinates, zoom }) => {
                setCenter(coordinates as [number, number])
                setZoom(zoom)
              }}
              maxZoom={8}
            >
              <Geographies geography={GEO_URL}>
                {({ geographies }) =>
                  geographies.map((geo) => (
                    <Geography
                      key={geo.rsmKey}
                      geography={geo}
                      style={{
                        default: {
                          fill: "var(--color-muted)",
                          stroke: "var(--color-background)",
                          strokeWidth: 0.4,
                          outline: "none",
                        },
                        hover: {
                          fill: "var(--color-secondary)",
                          outline: "none",
                        },
                        pressed: { fill: "var(--color-secondary)", outline: "none" },
                      }}
                    />
                  ))
                }
              </Geographies>

              {visible.map((s) => (
                <Marker
                  key={s.id}
                  coordinates={[s.lng, s.lat]}
                  onMouseEnter={() => setHovered(s)}
                  onMouseLeave={() => setHovered(null)}
                  onClick={() => openSpecies(s)}
                  style={{ default: { cursor: "pointer" } }}
                >
                  <circle
                    r={4 / Math.sqrt(zoom)}
                    fill={IUCN_META[s.iucn].color}
                    fillOpacity={0.85}
                    stroke="var(--color-background)"
                    strokeWidth={1 / Math.sqrt(zoom)}
                  />
                </Marker>
              ))}
            </ZoomableGroup>
          </ComposableMap>
        </div>
      </Card>

      <p className="text-xs text-muted-foreground">
        Showing {formatNumber(visible.length)} specimens. Drag to pan, scroll or use controls to
        zoom, and click any marker to inspect its genomic metadata.
      </p>

      <SpeciesDetailSheet species={selected} open={open} onOpenChange={setOpen} />
    </div>
  )
}

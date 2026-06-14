"use client"

import { useCallback, useEffect, useState } from "react"
import { useRouter, useSearchParams } from "next/navigation"
import { LayoutDashboard, List, ScatterChart } from "lucide-react"
import type { SpecimenSpeciesRow, TaxonRollup } from "@/lib/taxonomy-mock/types"
import { AtlasDetail } from "@/components/taxonomy/atlas/AtlasDetail"
import { AtlasSpeciesGrid } from "@/components/taxonomy/atlas/AtlasSpeciesGrid"
import { AtlasScatterPanel } from "@/components/taxonomy/atlas/AtlasScatterPanel"
import { cn } from "@/lib/utils"

export type AtlasPanelView = "overview" | "species" | "scatter"

const VIEWS: { id: AtlasPanelView; label: string; icon: typeof LayoutDashboard }[] = [
  { id: "overview", label: "Overview", icon: LayoutDashboard },
  { id: "species", label: "Species", icon: List },
  { id: "scatter", label: "Scatter", icon: ScatterChart },
]

export function parseAtlasView(raw: string | null): AtlasPanelView {
  if (raw === "species" || raw === "scatter") return raw
  return "overview"
}

function parseView(raw: string | null): AtlasPanelView {
  return parseAtlasView(raw)
}

export function AtlasRightPanel({
  row,
  species,
  selectedTaxid,
  genusName,
  onSelectAncestor,
  onJumpToGenus,
  layerId,
}: {
  row: TaxonRollup
  species: SpecimenSpeciesRow[]
  selectedTaxid: number
  genusName: string
  onSelectAncestor: (taxid: number) => void
  onJumpToGenus: () => void
  layerId: string
}) {
  const router = useRouter()
  const searchParams = useSearchParams()
  const [view, setViewState] = useState<AtlasPanelView>(() =>
    parseView(searchParams.get("view")),
  )

  useEffect(() => {
    setViewState(parseView(searchParams.get("view")))
  }, [searchParams])

  const setView = useCallback(
    (next: AtlasPanelView) => {
      setViewState(next)
      const params = new URLSearchParams(searchParams.toString())
      if (next === "overview") {
        params.delete("view")
      } else {
        params.set("view", next)
      }
      const qs = params.toString()
      router.replace(qs ? `/taxonomy/atlas?${qs}` : "/taxonomy/atlas", {
        scroll: false,
      })
    },
    [router, searchParams],
  )

  return (
    <div className="relative flex min-h-0 flex-1 flex-col">
      <div
        className={cn(
          "min-h-0 flex-1",
          view === "scatter" ? "flex flex-col overflow-hidden" : "overflow-y-auto",
        )}
      >
        {view === "overview" && (
          <div className="mx-auto max-w-5xl pb-16">
            <AtlasDetail row={row} onSelectAncestor={onSelectAncestor} />
          </div>
        )}
        {view === "species" && (
          <div className="mx-auto max-w-5xl pb-16">
            <AtlasSpeciesGrid
              species={species}
              genusName={genusName}
              onJumpToGenus={onJumpToGenus}
            />
          </div>
        )}
        {view === "scatter" && (
          <AtlasScatterPanel
            row={row}
            selectedTaxid={selectedTaxid}
            layerId={layerId}
            className="pb-14"
          />
        )}
      </div>

      <div className="pointer-events-none absolute inset-x-0 bottom-4 z-20 flex justify-center px-4">
        <div
          className="atlas-view-toggle pointer-events-auto flex items-center gap-0.5 rounded-full border border-white/10 bg-background/65 p-1 shadow-lg backdrop-blur-md"
          role="tablist"
          aria-label="Detail panel view"
        >
          {VIEWS.map(({ id, label, icon: Icon }) => (
            <button
              key={id}
              type="button"
              role="tab"
              aria-selected={view === id}
              onClick={() => setView(id)}
              className={cn(
                "inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 text-xs font-medium transition-colors",
                view === id
                  ? "bg-background text-foreground shadow-sm"
                  : "text-muted-foreground hover:text-foreground",
              )}
            >
              <Icon className="size-3.5" aria-hidden />
              {label}
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}

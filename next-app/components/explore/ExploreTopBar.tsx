"use client"

import { useEffect } from "react"
import { ChevronRight, ListTree, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { PIPELINE_LEGEND_ITEMS } from "@/lib/iucn/pipeline-legend"
import {
  getAncestorPath,
  getRollupStats,
  type IucnTaxonNode,
  type SelectedTaxon,
  useIucnTreeStore,
} from "@/lib/iucn/tree-store"

type Props = {
  selectedTaxon: SelectedTaxon | null
  drawerOpen: boolean
  dataFilter: string | null
  onBrowseToggle: () => void
  onSelectTaxon: (taxon: SelectedTaxon | null) => void
  onDataFilterChange: (filterId: string | null) => void
}

function formatCount(count: number): string {
  if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M`
  if (count >= 1_000) return `${(count / 1_000).toFixed(count >= 10_000 ? 0 : 1)}k`
  return String(count)
}

function DataChip({
  label,
  short,
  count,
  active,
  disabled,
  onClick,
}: {
  label: string
  short: string
  count: number
  active: boolean
  disabled?: boolean
  onClick: () => void
}) {
  return (
    <button
      type="button"
      title={label}
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "shrink-0 rounded-md border px-2 py-0.5 text-[11px] font-medium tabular-nums transition-colors",
        active
          ? "border-primary bg-primary/15 text-foreground ring-1 ring-primary/30"
          : "border-border/60 bg-secondary/40 text-muted-foreground hover:bg-secondary/70 hover:text-foreground",
        disabled && "pointer-events-none opacity-40",
      )}
    >
      {short}
      <span className="ml-1 opacity-70">{formatCount(count)}</span>
    </button>
  )
}

function FunnelSegment({
  node,
  maxCount,
  active,
  onClick,
}: {
  node: IucnTaxonNode
  maxCount: number
  active: boolean
  onClick: () => void
}) {
  const widthPct = Math.max(18, Math.round((node.speciesCountTotal / maxCount) * 100))
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "group flex min-w-0 flex-col items-center gap-0.5 transition-opacity",
        active ? "opacity-100" : "opacity-70 hover:opacity-100",
      )}
    >
      <div
        className={cn(
          "h-1.5 rounded-full bg-primary/70 transition-all group-hover:bg-primary",
          active && "bg-primary",
        )}
        style={{ width: `${widthPct}px`, minWidth: "1.5rem", maxWidth: "6rem" }}
      />
      <span className="max-w-[5.5rem] truncate text-[10px] font-medium uppercase tracking-wide text-muted-foreground">
        {node.rank}
      </span>
      <span className="max-w-[5.5rem] truncate text-xs font-medium">{node.taxonName}</span>
      <span className="text-[10px] tabular-nums text-muted-foreground">
        {formatCount(node.speciesCountTotal)}
      </span>
    </button>
  )
}

export function ExploreTopBar({
  selectedTaxon,
  drawerOpen,
  dataFilter,
  onBrowseToggle,
  onSelectTaxon,
  onDataFilterChange,
}: Props) {
  const { index, status, load } = useIucnTreeStore()
  const path = selectedTaxon ? getAncestorPath(index, selectedTaxon.taxonKey) : []
  const maxCount = path[0]?.speciesCountTotal ?? 1
  const stats = getRollupStats(index, selectedTaxon)

  useEffect(() => {
    if (status === "idle") void load()
  }, [status, load])

  const handleDataChipClick = (id: string, count: number) => {
    if (count <= 0) return
    if (dataFilter === id) onDataFilterChange(null)
    else onDataFilterChange(id)
  }

  return (
    <header className="flex h-14 shrink-0 items-center gap-2 border-b border-border bg-background/95 px-3 backdrop-blur supports-backdrop-filter:bg-background/80 md:gap-3 md:px-4">
      <Button
        variant={drawerOpen ? "secondary" : "outline"}
        size="sm"
        onClick={onBrowseToggle}
        className="shrink-0 gap-1.5"
      >
        <ListTree className="size-4" />
        Browse
      </Button>

      {stats ? (
        <div className="flex min-w-0 shrink items-center gap-1 overflow-x-auto pb-0.5">
          {PIPELINE_LEGEND_ITEMS.map((item) => {
            const count = stats[item.countField]
            return (
              <DataChip
                key={item.id}
                label={item.label}
                short={item.short}
                count={count}
                active={dataFilter === item.id}
                disabled={count <= 0}
                onClick={() => handleDataChipClick(item.id, count)}
              />
            )
          })}
        </div>
      ) : null}

      <div className="min-w-0 flex-1 border-l border-border/60 pl-2 md:pl-3">
        {path.length > 0 ? (
          <div className="flex min-w-0 items-end gap-2 overflow-x-auto pb-0.5">
            {path.map((node, indexInPath) => (
              <div key={node.taxonKey} className="flex shrink-0 items-end gap-2">
                {indexInPath > 0 ? (
                  <ChevronRight className="mb-4 size-3.5 shrink-0 text-muted-foreground/50" />
                ) : null}
                <FunnelSegment
                  node={node}
                  maxCount={maxCount}
                  active={node.taxonKey === selectedTaxon?.taxonKey}
                  onClick={() =>
                    onSelectTaxon({
                      taxonKey: node.taxonKey,
                      taxonName: node.taxonName,
                      rank: node.rank,
                    })
                  }
                />
              </div>
            ))}
          </div>
        ) : (
          <p className="truncate text-sm text-muted-foreground">
            All IUCN assessed species — select a taxon to filter the scatterplot
          </p>
        )}
      </div>

      {selectedTaxon ? (
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={() => onSelectTaxon(null)}
          className="shrink-0"
          title="Clear selection"
        >
          <X className="size-4" />
        </Button>
      ) : null}
    </header>
  )
}

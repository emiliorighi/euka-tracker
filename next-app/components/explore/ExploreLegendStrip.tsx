"use client"

import { useEffect, useMemo } from "react"
import { cn } from "@/lib/utils"
import { iucnLegendItems } from "@/lib/scatter/encoding"
import type { RollupCountFields } from "@/lib/iucn/pipeline-legend"
import {
  getRollupStats,
  type SelectedTaxon,
  useIucnTreeStore,
} from "@/lib/iucn/tree-store"

const IUCN_COUNT_FIELD: Record<string, keyof RollupCountFields> = {
  lc: "speciesCountLc",
  nt: "speciesCountNt",
  vu: "speciesCountVu",
  en: "speciesCountEn",
  cr: "speciesCountCr",
  dd: "speciesCountDd",
  ew: "speciesCountEw",
  ex: "speciesCountEx",
  ne: "speciesCountNe",
}

function formatCount(count: number): string {
  if (count >= 1_000_000) return `${(count / 1_000_000).toFixed(1)}M`
  if (count >= 10_000) return `${Math.round(count / 1_000)}k`
  if (count >= 1_000) return `${(count / 1_000).toFixed(1)}k`
  return count.toLocaleString()
}

type ChipProps = {
  label: string
  short: string
  color: string
  count: number
  active: boolean
  disabled?: boolean
  onClick: () => void
}

function LegendChip({ label, short, color, count, active, disabled, onClick }: ChipProps) {
  return (
    <button
      type="button"
      title={label}
      disabled={disabled}
      onClick={onClick}
      className={cn(
        "flex shrink-0 flex-col items-center gap-0.5 rounded-lg border px-2.5 py-1.5 transition-colors",
        active
          ? "border-primary bg-primary/15 ring-1 ring-primary/40"
          : "border-border/60 bg-background/80 hover:bg-secondary/60",
        disabled && "pointer-events-none opacity-40",
      )}
    >
      <span className="flex items-center gap-1.5 text-[11px] font-medium">
        <span className="size-2 rounded-full" style={{ backgroundColor: color }} aria-hidden />
        {short}
      </span>
      <span className="text-[10px] tabular-nums text-muted-foreground">{formatCount(count)}</span>
    </button>
  )
}

type Props = {
  iucnFilter: string | null
  selectedTaxon: SelectedTaxon | null
  onFilterChange: (filterId: string | null) => void
}

export function ExploreLegendStrip({ iucnFilter, selectedTaxon, onFilterChange }: Props) {
  const { status, load, index } = useIucnTreeStore()

  useEffect(() => {
    if (status === "idle") void load()
  }, [status, load])

  const stats = useMemo(
    () => getRollupStats(index, selectedTaxon),
    [index, selectedTaxon],
  )

  const iucnItems = useMemo(() => iucnLegendItems(), [])

  const activeLabel = useMemo(() => {
    if (!iucnFilter) return null
    return iucnItems.find((item) => item.id === iucnFilter)?.label ?? null
  }, [iucnFilter, iucnItems])

  const handleChipClick = (id: string, count: number) => {
    if (count <= 0) return
    if (iucnFilter === id) onFilterChange(null)
    else onFilterChange(id)
  }

  return (
    <div className="pointer-events-none absolute inset-x-0 bottom-4 z-40 flex justify-center px-3">
      <div className="pointer-events-auto max-w-[min(100%,56rem)] rounded-xl border border-border/80 bg-background/90 p-3 shadow-lg backdrop-blur-md">
        <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
          <div className="min-w-0">
            <p className="truncate text-xs font-medium text-foreground">
              {stats ? (
                <>
                  {stats.label}
                  <span className="ml-1.5 font-normal text-muted-foreground">
                    · {stats.speciesCountTotal.toLocaleString()} species
                  </span>
                </>
              ) : (
                "Loading counts…"
              )}
            </p>
            {activeLabel ? (
              <p className="text-[10px] text-muted-foreground">Showing {activeLabel} only</p>
            ) : null}
          </div>

          {iucnFilter ? (
            <button
              type="button"
              onClick={() => onFilterChange(null)}
              className="shrink-0 text-[11px] text-muted-foreground underline-offset-2 hover:text-foreground hover:underline"
            >
              Clear
            </button>
          ) : null}
        </div>

        <div className="flex gap-1.5 overflow-x-auto pb-0.5">
          {stats ? (
            <>
              <LegendChip
                label="All categories"
                short="All"
                color="#94a3b8"
                count={stats.speciesCountTotal}
                active={iucnFilter === null}
                onClick={() => onFilterChange(null)}
              />
              {iucnItems.map((item) => {
                const count = stats[IUCN_COUNT_FIELD[item.id]!] ?? 0
                return (
                  <LegendChip
                    key={item.id}
                    label={item.label}
                    short={item.short}
                    color={item.color}
                    count={count}
                    active={iucnFilter === item.id}
                    disabled={count <= 0}
                    onClick={() => handleChipClick(item.id, count)}
                  />
                )
              })}
            </>
          ) : null}
        </div>
      </div>
    </div>
  )
}

"use client"

import { useState } from "react"
import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import { formatNumber } from "@/lib/taxonomy-mock"
import { GhostCladeHint } from "./GhostCladeHint"
import { cn } from "@/lib/utils"

interface Band {
  key: string
  label: string
  value: number
}

function buildBands(row: TaxonRollup): Band[] {
  return [
    { key: "ncbi", label: "NCBI species", value: row.species_count_ncbi },
    { key: "reads", label: "With reads", value: row.species_with_reads },
    { key: "assembly", label: "With assembly", value: row.species_with_assembly },
    { key: "annotation", label: "With annotation", value: row.species_with_annotation },
    { key: "triple", label: "Full triple", value: row.species_full_triple },
  ]
}

function buildIucnBands(row: TaxonRollup): Band[] {
  return [
    { key: "ncbi", label: "NCBI species", value: row.species_count_ncbi },
    { key: "assessed", label: "IUCN assessed", value: row.species_iucn_assessed },
    { key: "threatened", label: "Threatened", value: row.species_threatened },
  ]
}

function BandColumn({
  title,
  bands,
  maxHeight = 320,
  accent = "var(--primary)",
  onBandClick,
}: {
  title: string
  bands: Band[]
  maxHeight?: number
  accent?: string
  onBandClick?: (band: Band, pctParent: string) => void
}) {
  const top = bands[0]?.value ?? 1
  return (
    <div className="flex flex-col items-center gap-2">
      <h3 className="text-xs font-medium uppercase tracking-widest text-muted-foreground">{title}</h3>
      <div className="flex flex-col-reverse gap-1" style={{ height: maxHeight }}>
        {bands.map((band, i) => {
          const h = top > 0 ? (band.value / top) * maxHeight : 0
          const parent = i > 0 ? bands[i - 1].value : band.value
          const pctParent = parent > 0 ? ((band.value / parent) * 100).toFixed(0) : "—"
          return (
            <button
              key={band.key}
              type="button"
              onClick={() => onBandClick?.(band, pctParent)}
              className="relative flex w-20 flex-col justify-end rounded-md border border-border/60 transition-all duration-300 hover:border-primary/40 md:w-24"
              style={{
                height: Math.max(h, band.key === "ncbi" ? maxHeight : 8),
                background: `linear-gradient(to top, ${accent}${i === 0 ? "33" : "55"}, ${accent}${i === 0 ? "18" : "28"})`,
              }}
              title={`${band.label}: ${formatNumber(band.value)}`}
            >
              <div className="absolute inset-x-0 bottom-1 px-1 text-center">
                <p className="font-mono text-[10px] tabular-nums">{formatNumber(band.value)}</p>
                {i > 0 && (
                  <p className="text-[8px] text-muted-foreground">{pctParent}% of above</p>
                )}
              </div>
            </button>
          )
        })}
      </div>
      <div className="flex flex-col gap-0.5 text-center">
        {bands.slice(1).map((b) => (
          <span key={b.key} className="text-[10px] text-muted-foreground">
            {b.label}
          </span>
        ))}
      </div>
    </div>
  )
}

export function FunnelCathedral({
  row,
  className,
  maxHeight = 280,
}: {
  row: TaxonRollup
  className?: string
  maxHeight?: number
}) {
  const [bandNote, setBandNote] = useState<string | null>(null)
  const genomic = buildBands(row)
  const iucn = buildIucnBands(row)

  const onBandClick = (band: Band, pctParent: string) => {
    setBandNote(`${band.label}: ${formatNumber(band.value)} (${pctParent}% of stage above)`)
  }

  return (
    <div className={cn("flex min-w-0 flex-col items-center gap-4", className)}>
      {row.species_count_matrix <= 0 && <GhostCladeHint row={row} />}
      <div
        key={row.taxid}
        className="flex flex-wrap items-end justify-center gap-6 md:gap-10"
      >
        <BandColumn
          title="Genomic funnel"
          bands={genomic}
          accent="var(--primary)"
          maxHeight={maxHeight}
          onBandClick={onBandClick}
        />
        <BandColumn
          title="Conservation"
          bands={iucn}
          accent="var(--risk-amber)"
          maxHeight={maxHeight}
          onBandClick={onBandClick}
        />
      </div>
      {bandNote && (
        <p className="max-w-sm text-center text-xs text-muted-foreground">{bandNote}</p>
      )}
    </div>
  )
}

export function FunnelDiffRow({
  label,
  left,
  right,
}: {
  label: string
  left: number
  right: number
}) {
  const max = Math.max(left, right, 1)
  return (
    <div className="space-y-1">
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>{label}</span>
        <span className="font-mono tabular-nums">
          {formatNumber(left)} vs {formatNumber(right)}
        </span>
      </div>
      <div className="flex h-2 gap-1">
        <div className="h-full rounded-l bg-primary/60" style={{ width: `${(left / max) * 50}%` }} />
        <div className="h-full rounded-r bg-chart-2/60" style={{ width: `${(right / max) * 50}%` }} />
      </div>
    </div>
  )
}

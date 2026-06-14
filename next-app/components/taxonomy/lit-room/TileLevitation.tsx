"use client"

import type { LevitationDetail } from "./lit-room-utils"
import { LitScientificName } from "./LitScientificName"
import { SpecimenGlyphs } from "./SpecimenGlyphs"
import type { SpecimenSpeciesRow } from "@/lib/taxonomy-mock/types"
import { cn } from "@/lib/utils"

export function TileLevitation({
  detail,
  row,
  open,
  onClose,
  levitationRef,
}: {
  detail: LevitationDetail | null
  row: SpecimenSpeciesRow | null
  open: boolean
  onClose: () => void
  levitationRef?: React.RefObject<HTMLDivElement | null>
}) {
  if (!open || !detail || !row) return null

  return (
    <>
      <div
        className="tile-levitation-backdrop lit-tile-lift-backdrop fixed inset-0 z-40 bg-black/60 backdrop-blur-[2px]"
        aria-hidden
        onClick={onClose}
      />
      <div
        ref={levitationRef}
        className="tile-levitation-card lit-tile-lift-open fixed left-1/2 top-1/2 z-50 w-[min(22rem,calc(100vw-2rem))] -translate-x-1/2 -translate-y-1/2"
        role="dialog"
        aria-modal="true"
        aria-labelledby="levitation-title"
      >
        <div className="tile-levitation-inner overflow-hidden rounded-2xl border border-primary/30 bg-card shadow-[0_0_60px_oklch(0.72_0.16_152/0.2)]">
          <div className="tile-levitation-glow pointer-events-none absolute inset-0 bg-gradient-to-b from-primary/10 to-transparent" aria-hidden />
          <div className="relative space-y-4 p-5">
            <div className="flex items-start justify-between gap-3">
              <div className="min-w-0 space-y-1">
                <p className="text-[10px] uppercase tracking-widest text-primary">Levitated specimen</p>
                <h2 id="levitation-title">
                  <LitScientificName name={detail.scientificName} className="text-lg" />
                </h2>
                <p className="text-xs text-muted-foreground">{detail.genusName}</p>
              </div>
              <button
                type="button"
                onClick={onClose}
                className="shrink-0 rounded-md border border-white/10 px-2 py-1 text-xs text-muted-foreground hover:bg-white/5"
              >
                Esc
              </button>
            </div>

            <SpecimenGlyphs row={row} />

            <dl className="grid grid-cols-2 gap-2 text-sm">
              <Stat label="Runs" value={String(detail.runCount)} />
              <Stat label="Assemblies" value={String(detail.assemblyCount)} />
              <Stat label="Annotations" value={String(detail.annotationCount)} />
              <Stat label="Red list" value={detail.redlist} />
              <Stat label="Genome" value={`${detail.genomeSizeMb.toFixed(1)} Mb`} />
              <Stat label="GC" value={`${detail.gcPercent.toFixed(1)}%`} />
              <Stat label="N50" value={`${detail.scaffoldN50Mb.toFixed(2)} Mb`} />
              <Stat label="BUSCO" value={`${detail.busco.toFixed(1)}%`} />
            </dl>

            <p className="rounded-lg border border-white/10 bg-secondary/30 px-3 py-2 text-xs text-muted-foreground">
              Assembly level: <span className="text-foreground">{detail.assemblyLevel}</span>
            </p>
          </div>
        </div>
      </div>
    </>
  )
}

function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-white/8 bg-black/20 px-2 py-1.5">
      <dt className="text-[10px] uppercase tracking-wide text-muted-foreground">{label}</dt>
      <dd className="font-mono text-sm tabular-nums">{value}</dd>
    </div>
  )
}

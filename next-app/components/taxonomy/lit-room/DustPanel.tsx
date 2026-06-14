"use client"

import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import { LitScientificName } from "./LitScientificName"
import { cn } from "@/lib/utils"

export function DustPanel({
  rows,
  onDrill,
  disabled,
}: {
  rows: TaxonRollup[]
  onDrill: (row: TaxonRollup) => void
  disabled?: boolean
}) {
  if (rows.length === 0) return null

  return (
    <div className="dust-panel max-h-40 overflow-auto rounded-lg border border-dashed border-white/15 bg-black/20">
      <ul className="divide-y divide-white/5">
        {rows.map((row) => (
          <li key={row.taxid}>
            <button
              type="button"
              disabled={disabled}
              onClick={() => onDrill(row)}
              className="flex w-full items-center justify-between gap-2 px-2 py-1.5 text-left hover:bg-white/5 disabled:opacity-50"
            >
              <LitScientificName name={row.scientific_name} className="min-w-0 truncate text-xs" />
              <span className="shrink-0 font-mono text-[10px] tabular-nums text-muted-foreground">
                {row.species_count_matrix.toLocaleString()}
              </span>
            </button>
          </li>
        ))}
      </ul>
    </div>
  )
}

"use client"

import type { CSSProperties } from "react"
import { pctCatalog } from "@/lib/taxonomy-mock"
import { getRankColor, getRankColorSolid } from "@/lib/taxonomy/rank-colors"
import { TaxonName } from "@/components/taxonomy/TaxonName"
import { ATLAS_TREE_GUTTER_REM, ATLAS_TREE_INDENT_REM } from "./atlas-tree-layout"
import type { AtlasFlatRow } from "./atlas-tree-layout-model"
import {
  ATLAS_TREE_ROW_CARD,
  ATLAS_TREE_ROW_HOVER,
  ATLAS_TREE_ROW_SELECTED,
} from "./atlas-tree-row-classes"
import { cn } from "@/lib/utils"

export function AtlasTreeRow({
  flatRow,
  selectedTaxid,
  pinActive,
  hidePinBand,
  onSelect,
}: {
  flatRow: AtlasFlatRow
  selectedTaxid: number
  pinActive: boolean
  hidePinBand: boolean
  onSelect: (taxid: number) => void
}) {
  const { row } = flatRow
  const selected = selectedTaxid === row.taxid
  const lit = pctCatalog(row)
  const ghostSelected = selected && pinActive
  const hideCard = ghostSelected || hidePinBand

  const rowStyle: CSSProperties = {
    paddingLeft: `${row.depth_from_eukaryota * ATLAS_TREE_INDENT_REM}rem`,
  }

  return (
    <div className="atlas-tree-node w-full" data-atlas-node={row.taxid}>
      <div
        className={cn(
          "atlas-tree-node-row relative flex w-full min-w-0 pointer-events-none",
          ghostSelected && "atlas-tree-node-row-ghost",
        )}
        style={rowStyle}
        {...(selected && !pinActive ? { "data-atlas-selected-node": row.taxid } : {})}
      >
        <div
          className="shrink-0 self-stretch"
          style={{ width: `${ATLAS_TREE_GUTTER_REM}rem` }}
          aria-hidden
        />

        <button
          type="button"
          data-atlas-node-row={row.taxid}
          {...(hidePinBand ? { "data-atlas-pin-band-hidden": row.taxid } : {})}
          onClick={() => onSelect(row.taxid)}
          className={cn(
            ATLAS_TREE_ROW_CARD,
            hideCard ? "invisible pointer-events-none" : "pointer-events-auto",
            selected && !hideCard
              ? ATLAS_TREE_ROW_SELECTED
              : !hideCard && ATLAS_TREE_ROW_HOVER,
          )}
        >
          <TaxonName name={row.scientific_name} className="min-w-0 truncate text-xs leading-tight" />
          <span
            className="shrink-0 rounded px-1 py-px text-[8px] uppercase tracking-wider"
            style={{
              color: getRankColorSolid(row.rank),
              backgroundColor: getRankColor(row.rank, 0.12),
            }}
          >
            {row.rank}
          </span>
          <span
            className="ml-auto h-1 w-6 shrink-0 overflow-hidden rounded-full bg-secondary/80"
            title={`${(lit * 100).toFixed(1)}% catalog`}
          >
            <span
              className="block h-full rounded-full"
              style={{
                width: `${Math.round(lit * 100)}%`,
                backgroundColor: getRankColorSolid(row.rank),
              }}
            />
          </span>
        </button>
      </div>
    </div>
  )
}

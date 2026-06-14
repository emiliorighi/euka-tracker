"use client"

import type { CSSProperties, RefObject } from "react"
import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import { pctCatalog } from "@/lib/taxonomy-mock"
import { getRankColor, getRankColorSolid } from "@/lib/taxonomy/rank-colors"
import { TaxonName } from "@/components/taxonomy/TaxonName"
import { ATLAS_TREE_GUTTER_REM, ATLAS_TREE_INDENT_REM } from "./atlas-tree-layout"
import {
  ATLAS_TREE_ROW_CARD,
  ATLAS_TREE_ROW_SELECTED,
} from "./atlas-tree-row-classes"
import { cn } from "@/lib/utils"

export function AtlasTreeSelectedPin({
  row,
  active,
  onSelect,
  pinRef,
}: {
  row: TaxonRollup
  active: boolean
  onSelect: (taxid: number) => void
  pinRef?: RefObject<HTMLButtonElement | null>
}) {
  const lit = pctCatalog(row)
  const rowStyle: CSSProperties = {
    paddingLeft: `${row.depth_from_eukaryota * ATLAS_TREE_INDENT_REM}rem`,
  }

  return (
    <div
      className={cn(
        "atlas-tree-pin-slot sticky top-0 h-0 w-full overflow-visible",
        active ? "z-[30]" : "z-20",
      )}
      aria-hidden={!active}
    >
      <div
        className={cn(
          "atlas-tree-node-row atlas-tree-pin-row pointer-events-none flex w-full min-w-0",
          active ? "atlas-tree-pin-row-active visible" : "invisible",
        )}
        style={{ ...rowStyle, height: "var(--atlas-tree-row-height)" }}
        data-atlas-selected-node={row.taxid}
      >
        <div
          className="shrink-0 self-stretch"
          style={{ width: `${ATLAS_TREE_GUTTER_REM}rem` }}
          aria-hidden
        />
        <button
          ref={pinRef}
          type="button"
          data-atlas-selected-pin={row.taxid}
          onClick={() => onSelect(row.taxid)}
          className={cn(
            ATLAS_TREE_ROW_CARD,
            "pointer-events-auto",
            active && ATLAS_TREE_ROW_SELECTED,
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

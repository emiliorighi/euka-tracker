import type { CSSProperties } from "react"
import type { LitTreeRow } from "@/lib/taxonomy/lit-tree"

/** Horizontal indent per depth level (matches lit-tree.css) */
export const LIT_TREE_INDENT_REM = 1.25

export function rowIndentStyle(depth: number): CSSProperties {
  return { paddingLeft: `${depth * LIT_TREE_INDENT_REM}rem` }
}

export function findRowIndex(rows: LitTreeRow[], taxid: number): number {
  return rows.findIndex((r) => r.row.taxid === taxid)
}

export function segmentRows(rows: LitTreeRow[]): LitTreeRow[] {
  return rows.filter((r) => r.segmentTaxid != null)
}

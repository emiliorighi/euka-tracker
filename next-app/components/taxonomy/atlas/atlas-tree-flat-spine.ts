import { ATLAS_TREE_INDENT_REM, ATLAS_TREE_GUTTER_REM } from "./atlas-tree-layout"

/** Flat-row vertical trunk X at gutter center (matches normal connector trunks). */
export function flatRowTrunkCenterX(
  rowLeft: number,
  paddingLeft: number,
  gutterHalf: number,
): number {
  return rowLeft + paddingLeft + gutterHalf
}

export function trunkXAtDepth(
  selectedTrunkCenterX: number,
  selectedDepth: number,
  effectiveIndent: number,
  depthFromEukaryota: number,
): number {
  return selectedTrunkCenterX + (depthFromEukaryota - selectedDepth) * effectiveIndent
}

export function isEdgeOnSelectionPath(
  parentTaxid: number,
  childTaxid: number | undefined,
  pathTaxids: Set<number>,
): boolean {
  if (childTaxid == null) return false
  return pathTaxids.has(parentTaxid) && pathTaxids.has(childTaxid)
}

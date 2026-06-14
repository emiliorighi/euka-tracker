import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import { getAtlasChildrenOf, getAtlasRowById } from "@/lib/atlas-taxonomy"
import {
  ATLAS_TREE_GUTTER_REM,
  ATLAS_TREE_INDENT_REM,
  ATLAS_TREE_MIN_WIDTH_REM,
  ATLAS_TREE_ROW_HEIGHT_REM,
} from "./atlas-tree-layout"
import { trunkXAtDepth } from "./atlas-tree-flat-spine"

export type AtlasFlatRow = {
  taxid: number
  depth: number
  parentTaxid: number | null
  row: TaxonRollup
  index: number
}

export type AtlasRowRect = {
  taxid: number
  index: number
  top: number
  midY: number
  trunkX: number
  cardLeft: number
  cardRight: number
}

export type AtlasLayoutMetrics = {
  fontSizePx: number
  indentPx: number
  gutterPx: number
  gutterHalf: number
  rowHeightPx: number
}

export type AtlasTreeLayout = {
  flatRows: AtlasFlatRow[]
  rowByTaxid: Map<number, AtlasRowRect>
  contentHeight: number
  contentWidth: number
  metrics: AtlasLayoutMetrics
}

export type AtlasPinContext = {
  rowY: number
  selectedTrunkCenterX: number
  selectedDepth: number
  effectiveIndent: number
  cardLeft: number
  selectedTaxid: number
  immediateParentTaxid: number
}

export type AtlasPinState = {
  pinActive: boolean
  pinRowY: number
  pin: AtlasPinContext | null
}

const PIN_SCROLL_THRESHOLD = 2
const PIN_VIEWPORT_THRESHOLD = 1

export function flattenVisibleTree(
  rootTaxid: number,
  isExpanded: (taxid: number) => boolean,
): AtlasFlatRow[] {
  const out: AtlasFlatRow[] = []

  function walk(taxid: number, parentTaxid: number | null) {
    const row = getAtlasRowById(taxid)
    if (!row) return
    out.push({
      taxid,
      depth: row.depth_from_eukaryota,
      parentTaxid,
      row,
      index: out.length,
    })
    if (!isExpanded(taxid)) return
    for (const child of getAtlasChildrenOf(taxid)) {
      walk(child.taxid, taxid)
    }
  }

  walk(rootTaxid, null)
  return out
}

export function computeMetrics(fontSizePx = 16): AtlasLayoutMetrics {
  const gutterPx = ATLAS_TREE_GUTTER_REM * fontSizePx
  return {
    fontSizePx,
    indentPx: ATLAS_TREE_INDENT_REM * fontSizePx,
    gutterPx,
    gutterHalf: gutterPx / 2,
    rowHeightPx: ATLAS_TREE_ROW_HEIGHT_REM * fontSizePx,
  }
}

export function buildAtlasTreeLayout(
  flatRows: AtlasFlatRow[],
  metrics: AtlasLayoutMetrics,
  contentWidth?: number,
): AtlasTreeLayout {
  const contentW = contentWidth ?? ATLAS_TREE_MIN_WIDTH_REM * metrics.fontSizePx
  const rowByTaxid = new Map<number, AtlasRowRect>()

  for (const flat of flatRows) {
    const paddingLeft = flat.depth * metrics.indentPx
    const trunkX = paddingLeft + metrics.gutterHalf
    const cardLeft = paddingLeft + metrics.gutterPx
    const top = flat.index * metrics.rowHeightPx
    const midY = top + metrics.rowHeightPx / 2
    rowByTaxid.set(flat.taxid, {
      taxid: flat.taxid,
      index: flat.index,
      top,
      midY,
      trunkX,
      cardLeft,
      cardRight: contentW - 8,
    })
  }

  return {
    flatRows,
    rowByTaxid,
    contentHeight: flatRows.length * metrics.rowHeightPx,
    contentWidth: contentW,
    metrics,
  }
}

export function buildAtlasTreeLayoutFromTree(
  rootTaxid: number,
  isExpanded: (taxid: number) => boolean,
  fontSizePx = 16,
  contentWidth?: number,
): AtlasTreeLayout {
  const metrics = computeMetrics(fontSizePx)
  const flatRows = flattenVisibleTree(rootTaxid, isExpanded)
  return buildAtlasTreeLayout(flatRows, metrics, contentWidth)
}

export function getRowIndex(layout: AtlasTreeLayout, taxid: number): number {
  return layout.rowByTaxid.get(taxid)?.index ?? -1
}

export function computePinState(
  layout: AtlasTreeLayout,
  scrollTop: number,
  selectionPath: TaxonRollup[],
  selectedTaxid: number,
): AtlasPinState {
  const selectedRect = layout.rowByTaxid.get(selectedTaxid)
  const pinRowY = scrollTop + layout.metrics.rowHeightPx / 2

  if (!selectedRect || selectionPath.length === 0) {
    return { pinActive: false, pinRowY, pin: null }
  }

  const scrolledPastNatural = scrollTop > selectedRect.top + PIN_SCROLL_THRESHOLD
  const rowTopInViewport = selectedRect.top - scrollTop
  const rowAboveClip = rowTopInViewport < PIN_VIEWPORT_THRESHOLD
  const pinActive = scrolledPastNatural && rowAboveClip

  if (!pinActive) {
    return { pinActive: false, pinRowY, pin: null }
  }

  const selectedRow = selectionPath[selectionPath.length - 1]!
  const selectedDepth = selectedRow.depth_from_eukaryota
  const paddingLeft = selectedDepth * layout.metrics.indentPx
  const effectiveIndent =
    selectedDepth > 0 ? paddingLeft / selectedDepth : layout.metrics.indentPx

  const pin: AtlasPinContext = {
    rowY: pinRowY,
    selectedTrunkCenterX: paddingLeft + layout.metrics.gutterHalf,
    selectedDepth,
    effectiveIndent,
    cardLeft: selectedRect.cardLeft,
    selectedTaxid: selectedRow.taxid,
    immediateParentTaxid:
      selectionPath.length >= 2
        ? selectionPath[selectionPath.length - 2]!.taxid
        : selectedRow.taxid,
  }

  return { pinActive: true, pinRowY, pin }
}

/** Rows whose vertical center overlaps the sticky pin band (content coordinates). */
export function taxidsInPinBand(
  layout: AtlasTreeLayout,
  pinRowY: number,
  selectedTaxid: number,
): Set<number> {
  const tolerance = layout.metrics.rowHeightPx * 0.55
  const hidden = new Set<number>()
  for (const flat of layout.flatRows) {
    if (flat.taxid === selectedTaxid) continue
    const rect = layout.rowByTaxid.get(flat.taxid)
    if (!rect) continue
    if (Math.abs(rect.midY - pinRowY) <= tolerance) hidden.add(flat.taxid)
  }
  return hidden
}

/**
 * Pin-band row cards to hide when pinned (connectors unaffected).
 * Ghost selected row is handled separately in AtlasTreeRow via pinActive + selectedTaxid.
 */
export function computeHiddenRowTaxids(
  layout: AtlasTreeLayout,
  pinState: AtlasPinState,
  selectedTaxid: number,
): Set<number> {
  if (!pinState.pinActive) return new Set()
  return taxidsInPinBand(layout, pinState.pinRowY, selectedTaxid)
}

export function syntheticPathRowLayout(
  row: TaxonRollup,
  pin: AtlasPinContext,
): Pick<AtlasRowRect, "trunkX" | "cardLeft" | "midY"> {
  const trunkX = trunkXAtDepth(
    pin.selectedTrunkCenterX,
    pin.selectedDepth,
    pin.effectiveIndent,
    row.depth_from_eukaryota,
  )
  const isSelected = row.taxid === pin.selectedTaxid
  return {
    trunkX,
    cardLeft: isSelected ? pin.cardLeft : trunkX,
    midY: pin.rowY,
  }
}

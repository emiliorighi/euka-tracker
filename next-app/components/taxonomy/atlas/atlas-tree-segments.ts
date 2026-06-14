/**
 * Atlas tree connector geometry — spec: repo connector.txt
 *
 * Parent P owns every `--` toward direct child C, always at **C's row Y** (never at P's row).
 * Node N's own row shows vertical `|` only — no self-row horizontal.
 * Root starts with `|` only. Pinned: ancestor flatPath trunk hops at pin rowY; when L≥4 the
 * last hop runs through IP to selected trunk (no separate IP flatPath); immediate parent
 * always owns terminal toCard into the selected card.
 * Vertical trunks always span natural parent midY → last child midY (never clipped at pin row).
 */

import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import {
  buildPathBreadcrumbHorizontals,
  edgeState,
  parentTrunkState,
} from "./connector-state"
import type { AtlasPinContext, AtlasTreeLayout } from "./atlas-tree-layout-model"

export type AtlasTreeEdge = {
  parentTaxid: number
  parentRank: string
  parentDepth: number
  childTaxid: number
  childRank: string
}

export type HorizontalRole = "toTrunk" | "toCard" | "flatPath"
export type VerticalRole = "childFan"

export type AtlasConnectorSegment = {
  ownerTaxid: number
  ownerRank: string
  childTaxid: number
  axis: "horizontal" | "vertical"
  role?: HorizontalRole
  verticalRole?: VerticalRole
  onPinRow?: boolean
  x1: number
  y1: number
  x2: number
  y2: number
}

type RowLayout = {
  trunkX: number
  cardLeft: number
  midY: number
}

/** Layout from flat row indices — never synthetic pin-row Y (vertical trunks). */
function naturalRowLayout(taxid: number, layout: AtlasTreeLayout): RowLayout | null {
  const rect = layout.rowByTaxid.get(taxid)
  if (!rect) return null
  return { trunkX: rect.trunkX, cardLeft: rect.cardLeft, midY: rect.midY }
}

function verticalParentMidY(
  parentTaxid: number,
  layout: AtlasTreeLayout,
  selectedTaxid: number,
  pathTaxids: Set<number> | null,
  pin: AtlasPinContext | null,
): number {
  const natural = naturalRowLayout(parentTaxid, layout)
  if (!natural) return 0
  const onPinRow =
    pin != null && pathTaxids?.has(parentTaxid) && parentTaxid === selectedTaxid
  return onPinRow ? pin!.rowY : natural.midY
}

function pushHorizontal(
  out: AtlasConnectorSegment[],
  opts: {
    ownerTaxid: number
    ownerRank: string
    childTaxid: number
    role: HorizontalRole
    x1: number
    y1: number
    x2: number
    onPinRow?: boolean
    rootMidY?: number | null
  },
) {
  if (opts.rootMidY != null && Math.abs(opts.y1 - opts.rootMidY) <= 2) return
  if (Math.abs(opts.x2 - opts.x1) <= 1) return
  out.push({
    ownerTaxid: opts.ownerTaxid,
    ownerRank: opts.ownerRank,
    childTaxid: opts.childTaxid,
    axis: "horizontal",
    role: opts.role,
    onPinRow: opts.onPinRow,
    x1: opts.x1,
    y1: opts.y1,
    x2: opts.x2,
    y2: opts.y1,
  })
}

type ChildEdgeLayout = {
  edge: AtlasTreeEdge
  onPathEdge: boolean
  trunkX: number
  cardLeft: number
  midY: number
}

/** Pass B trunk column: first off-path child trunk, else first child trunk. */
function bundleTrunkX(childLayouts: ChildEdgeLayout[]): number {
  const offPath = childLayouts.filter((c) => !c.onPathEdge)
  const trunkLayouts = offPath.length > 0 ? offPath : childLayouts
  return trunkLayouts[0]!.trunkX
}

function resolveHorizontalEndpoint(
  trunkX: number,
  child: { trunkX: number; cardLeft: number },
  childHasChildren: boolean,
  forceCard = false,
): { x2: number; role: HorizontalRole } {
  if (forceCard || !(childHasChildren && child.trunkX > trunkX + 1)) {
    return {
      x2: Math.max(child.cardLeft - 2, trunkX + 2),
      role: "toCard",
    }
  }
  return { x2: child.trunkX, role: "toTrunk" }
}

/** One visible edge P → C: parent-owned `--` at C's row, never zero length. */
function emitEdgeHorizontal(
  out: AtlasConnectorSegment[],
  opts: {
    ownerTaxid: number
    ownerRank: string
    childTaxid: number
    trunkX: number
    childLayout: ChildEdgeLayout
    childHasChildren: boolean
    onPinRow?: boolean
    rootMidY?: number | null
  },
) {
  const { trunkX, childLayout, childHasChildren } = opts
  const { x2, role } = resolveHorizontalEndpoint(trunkX, childLayout, childHasChildren)
  pushHorizontal(out, {
    ownerTaxid: opts.ownerTaxid,
    ownerRank: opts.ownerRank,
    childTaxid: opts.childTaxid,
    role,
    x1: trunkX,
    y1: childLayout.midY,
    x2,
    onPinRow: opts.onPinRow,
    rootMidY: opts.rootMidY,
  })
}

export function buildConnectorSegments({
  layout,
  edges,
  selectionPath,
  pathTaxids,
  pin,
  selectedTaxid,
  rootTaxid,
}: {
  layout: AtlasTreeLayout
  edges: AtlasTreeEdge[]
  selectionPath: TaxonRollup[]
  pathTaxids: Set<number> | null
  pin: AtlasPinContext | null
  selectedTaxid: number
  rootTaxid: number
}): AtlasConnectorSegment[] {
  const segments: AtlasConnectorSegment[] = []
  const pinActive = pin != null
  const pathSet = pinActive ? pathTaxids : null

  const childCount = new Map<number, number>()
  for (const edge of edges) {
    childCount.set(edge.parentTaxid, (childCount.get(edge.parentTaxid) ?? 0) + 1)
  }

  const rootLayout = naturalRowLayout(rootTaxid, layout)
  const rootMidY = rootLayout?.midY ?? null

  const byParent = new Map<number, AtlasTreeEdge[]>()
  for (const edge of edges) {
    const list = byParent.get(edge.parentTaxid) ?? []
    list.push(edge)
    byParent.set(edge.parentTaxid, list)
  }

  // --- Pass A: pinned breadcrumb horizontals (on-path, collapsed) ---
  if (pinActive && pin != null && selectionPath.length >= 2) {
    segments.push(...buildPathBreadcrumbHorizontals(selectionPath, pin, childCount))
  }

  // --- Pass A: off-path / natural horizontals ---
  for (const [parentTaxid, childEdges] of byParent) {
    const parentEdge = childEdges[0]!
    const parentLayout = naturalRowLayout(parentTaxid, layout)
    if (!parentLayout) continue

    const childLayouts = childEdges
      .map((edge) => {
        const state = edgeState(edge.parentTaxid, edge.childTaxid, pathSet, pinActive)
        const onPathEdge = state.lineage === "onPath"
        const childLayout = naturalRowLayout(edge.childTaxid, layout)
        if (!childLayout) return null
        return { edge, onPathEdge, ...childLayout }
      })
      .filter((c): c is ChildEdgeLayout => c != null)
      .sort((a, b) => a.midY - b.midY)

    if (childLayouts.length === 0) continue

    const trunkX = bundleTrunkX(childLayouts)

    for (const c of childLayouts) {
      const state = edgeState(c.edge.parentTaxid, c.edge.childTaxid, pathSet, pinActive)
      if (state.lineage === "onPath" && state.phase === "collapsed") continue

      if (pinActive && pin != null) {
        const natural = naturalRowLayout(c.edge.childTaxid, layout)
        const pinBandTol = layout.metrics.rowHeightPx * 0.55
        if (natural && Math.abs(natural.midY - pin.rowY) <= pinBandTol) continue
      }

      const childHasChildren = (childCount.get(c.edge.childTaxid) ?? 0) > 0
      const onPinRow =
        pin != null &&
        pathSet?.has(c.edge.childTaxid) &&
        c.edge.childTaxid === selectedTaxid

      emitEdgeHorizontal(segments, {
        ownerTaxid: parentTaxid,
        ownerRank: parentEdge.parentRank,
        childTaxid: c.edge.childTaxid,
        trunkX,
        childLayout: c,
        childHasChildren,
        onPinRow,
        rootMidY,
      })
    }
  }

  // --- Pass B: vertical trunks (natural row Y; full span including above pin row) ---
  for (const [parentTaxid, childEdges] of byParent) {
    const parentEdge = childEdges[0]!

    const childLayouts = childEdges
      .map((edge) => {
        const onPathEdge =
          pathSet != null &&
          edgeState(edge.parentTaxid, edge.childTaxid, pathSet, pinActive).lineage === "onPath"
        const childLayout = naturalRowLayout(edge.childTaxid, layout)
        if (!childLayout) return null
        return { edge, onPathEdge, ...childLayout }
      })
      .filter((c): c is ChildEdgeLayout => c != null)
      .sort((a, b) => a.midY - b.midY)

    if (parentTrunkState(childLayouts.length) === "skip") continue

    const trunkX = bundleTrunkX(childLayouts)
    const lastChildMidY = childLayouts[childLayouts.length - 1]!.midY
    const pMidY = verticalParentMidY(parentTaxid, layout, selectedTaxid, pathSet, pin)
    const onPinRow = pin != null && pathSet?.has(parentTaxid) && parentTaxid === selectedTaxid

    if (lastChildMidY <= pMidY + 1) continue

    segments.push({
      ownerTaxid: parentTaxid,
      ownerRank: parentEdge.parentRank,
      childTaxid: childLayouts[0]!.edge.childTaxid,
      axis: "vertical",
      x1: trunkX,
      y1: pMidY,
      x2: trunkX,
      y2: lastChildMidY,
      onPinRow,
    })
  }

  return segments
}

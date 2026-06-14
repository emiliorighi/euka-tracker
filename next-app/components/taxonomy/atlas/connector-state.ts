/**
 * Lineage-based connector state — spec: repo connector.txt
 *
 * Each parent→child edge and parent trunk is classified once, then emitted.
 * Pinned mode collapses on-path horizontals to breadcrumb segments at pin.rowY;
 * vertical trunks always use natural row Y (full span, not clipped at pin row).
 */

import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import { isEdgeOnSelectionPath } from "./atlas-tree-flat-spine"
import type { AtlasPinContext } from "./atlas-tree-layout-model"
import { syntheticPathRowLayout } from "./atlas-tree-layout-model"
import type { AtlasConnectorSegment, HorizontalRole } from "./atlas-tree-segments"

export type Lineage = "onPath" | "offPath"
export type Phase = "natural" | "collapsed"

export type EdgeState = { lineage: Lineage; phase: Phase }

/** Classify a visible parent→child edge for horizontal emission. */
export function edgeState(
  parentTaxid: number,
  childTaxid: number,
  pathTaxids: Set<number> | null,
  pinActive: boolean,
): EdgeState {
  const onPath =
    pathTaxids != null && isEdgeOnSelectionPath(parentTaxid, childTaxid, pathTaxids)
  return {
    lineage: onPath ? "onPath" : "offPath",
    phase: onPath && pinActive ? "collapsed" : "natural",
  }
}

export type ParentTrunkState = "fullTrunk" | "skip"

/** Classify whether a parent should emit a vertical trunk segment. */
export function parentTrunkState(visibleChildCount: number): ParentTrunkState {
  return visibleChildCount > 0 ? "fullTrunk" : "skip"
}

type PathRowLayout = { trunkX: number; cardLeft: number; midY: number }

function pathRowLayout(row: TaxonRollup, pin: AtlasPinContext): PathRowLayout {
  return syntheticPathRowLayout(row, pin)
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
  },
) {
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

/**
 * Pinned breadcrumb horizontals at pin.rowY.
 * One flatPath hop per path ancestor; terminal toCard owned by immediate parent.
 * When L≥4, last ancestor hop absorbs IP→selected trunk stub (x2 override).
 */
export function buildPathBreadcrumbHorizontals(
  selectionPath: TaxonRollup[],
  pin: AtlasPinContext,
  childCount: Map<number, number>,
): AtlasConnectorSegment[] {
  const segments: AtlasConnectorSegment[] = []
  const L = selectionPath.length
  if (L < 2) return segments

  const selected = selectionPath[L - 1]!
  const selectedLayout = pathRowLayout(selected, pin)
  const immediateParent = selectionPath[L - 2]!
  const mergeIpFlatHop = L >= 4

  for (let i = 0; i <= L - 4; i++) {
    const parent = selectionPath[i]!
    const child = selectionPath[i + 1]!
    const grandchild = selectionPath[i + 2]!
    const childLayout = pathRowLayout(child, pin)
    const extendsThroughIp =
      mergeIpFlatHop && grandchild.taxid === immediateParent.taxid
    const { x2 } = extendsThroughIp
      ? { x2: selectedLayout.trunkX }
      : resolveHorizontalEndpoint(
          childLayout.trunkX,
          pathRowLayout(grandchild, pin),
          (childCount.get(grandchild.taxid) ?? 0) > 0,
        )
    pushHorizontal(segments, {
      ownerTaxid: parent.taxid,
      ownerRank: parent.rank,
      childTaxid: extendsThroughIp ? immediateParent.taxid : child.taxid,
      role: "flatPath",
      x1: childLayout.trunkX,
      y1: pin.rowY,
      x2,
      onPinRow: true,
    })
  }

  const ipLayout = pathRowLayout(immediateParent, pin)

  if (L >= 3 && !mergeIpFlatHop) {
    const selectedHasChildren = (childCount.get(selected.taxid) ?? 0) > 0
    const { x2: trunkHopX2 } = resolveHorizontalEndpoint(
      ipLayout.trunkX,
      selectedLayout,
      selectedHasChildren,
    )
    if (Math.abs(trunkHopX2 - ipLayout.trunkX) > 1) {
      pushHorizontal(segments, {
        ownerTaxid: immediateParent.taxid,
        ownerRank: immediateParent.rank,
        childTaxid: selected.taxid,
        role: "flatPath",
        x1: ipLayout.trunkX,
        y1: pin.rowY,
        x2: trunkHopX2,
        onPinRow: true,
      })
    }
  }

  const { x2: cardX2 } = resolveHorizontalEndpoint(
    selectedLayout.trunkX,
    selectedLayout,
    false,
    true,
  )
  pushHorizontal(segments, {
    ownerTaxid: immediateParent.taxid,
    ownerRank: immediateParent.rank,
    childTaxid: selected.taxid,
    role: "toCard",
    x1: selectedLayout.trunkX,
    y1: pin.rowY,
    x2: cardX2,
    onPinRow: true,
  })

  return segments
}

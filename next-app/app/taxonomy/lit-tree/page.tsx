"use client"

import { useCallback, useMemo } from "react"
import Link from "next/link"
import {
  EUKARYOTA_TAXID,
  getEukaryotaRow,
  getRowById,
  getSpecimenGenusTaxid,
  getSpecimenSlice,
} from "@/lib/taxonomy-mock"
import { getLitRoomMode } from "@/lib/taxonomy/lit-room"
import { LitTreeShell } from "@/components/taxonomy/lit-tree/LitTreeShell"
import { LitTreeStage } from "@/components/taxonomy/lit-tree/LitTreeStage"
import { LitTreePanel } from "@/components/taxonomy/lit-tree/LitTreePanel"
import { LitTreeRow } from "@/components/taxonomy/lit-tree/LitTreeRow"
import { useLitTreeNav } from "@/hooks/useLitTreeNav"
import { useLitTreeKeyboard } from "@/hooks/useLitTreeKeyboard"
import "@/components/taxonomy/lit-room/lit-room-tokens.css"
import "@/components/taxonomy/lit-tree/lit-tree.css"

export default function TaxonomyLitTreePage() {
  const {
    focusTaxid,
    selectedTaxid,
    focusExpanded,
    setFocusExpanded,
    rows,
    hasMoreAncestors,
    rootTaxid,
    jump,
    ascend,
    activateRow,
    cycleSelection,
    activateSelected,
  } = useLitTreeNav(EUKARYOTA_TAXID)

  const focus = useMemo(() => getRowById(focusTaxid) ?? getEukaryotaRow(), [focusTaxid])
  const mode = useMemo(() => getLitRoomMode(focusTaxid), [focusTaxid])
  const slice = getSpecimenSlice()

  useLitTreeKeyboard({
    onEscape: ascend,
    onArrowUp: () => cycleSelection(-1),
    onArrowDown: () => cycleSelection(1),
    onEnter: activateSelected,
  })

  const rootJump = useCallback(() => {
    if (rootTaxid != null) jump(rootTaxid)
  }, [rootTaxid, jump])

  return (
    <LitTreeShell
      focusRow={focus}
      headerExtra={
        <>
          <Link
            href={`/taxonomy/atlas?view=scatter`}
            className="inline-flex h-8 items-center rounded-md border border-border px-3 text-sm hover:bg-secondary/60"
          >
            Explore
          </Link>
          <button
            type="button"
            onClick={() => jump(getSpecimenGenusTaxid())}
            className="inline-flex h-8 items-center rounded-md bg-primary/15 px-3 text-sm text-primary hover:bg-primary/25"
          >
            Jump to {slice.genus_name}
          </button>
        </>
      }
    >
      <LitTreeStage>
        <LitTreePanel
          rows={rows}
          rootJump={
            hasMoreAncestors && rootTaxid != null
              ? { taxid: rootTaxid, onJump: rootJump }
              : undefined
          }
        >
          {(registerRow) =>
            rows.map((treeRow) => (
              <LitTreeRow
                key={treeRow.row.taxid}
                treeRow={treeRow}
                mode={mode}
                selected={selectedTaxid === treeRow.row.taxid}
                focusExpanded={treeRow.role === "focus" ? focusExpanded : undefined}
                onFocusExpandedChange={treeRow.role === "focus" ? setFocusExpanded : undefined}
                onActivate={activateRow}
                onRegister={registerRow}
              />
            ))
          }
        </LitTreePanel>
      </LitTreeStage>
    </LitTreeShell>
  )
}

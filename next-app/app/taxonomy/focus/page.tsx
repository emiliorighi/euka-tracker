"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import {
  EUKARYOTA_TAXID,
  getEukaryotaRow,
  getRowById,
  getSpeciesForTaxid,
  getSpecimenGenusTaxid,
  getSpecimenSlice,
} from "@/lib/taxonomy-mock"
import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import { getChildDeck, getParentBookmark } from "@/lib/taxonomy/focus-nav"
import { FocusStackShell } from "@/components/taxonomy/focus/FocusStackShell"
import { FocusStackLayout } from "@/components/taxonomy/focus/FocusStackLayout"
import { LeftSpineColumn } from "@/components/taxonomy/focus/LeftSpineColumn"
import { MobileAncestorBar } from "@/components/taxonomy/focus/AncestorSpine"
import { ParentBookmark } from "@/components/taxonomy/focus/ParentBookmark"
import { FocusHero } from "@/components/taxonomy/focus/FocusHero"
import { FocusSpeciesList } from "@/components/taxonomy/focus/FocusSpeciesList"
import { ChildColumn } from "@/components/taxonomy/focus/ChildColumn"
import { useFocusTransition } from "@/hooks/useFocusTransition"
import { useConceptKeyboard } from "@/hooks/useConceptKeyboard"
import { Button, buttonVariants } from "@/components/ui/button"
import Link from "next/link"
import { cn } from "@/lib/utils"
import "@/components/taxonomy/focus/spine-motion.css"

function clampIndex(index: number, length: number): number {
  if (length <= 0) return 0
  return Math.max(0, Math.min(index, length - 1))
}

export default function TaxonomyFocusPage() {
  const { focusTaxid, heroHidden, heroRef, isBusy, navigate } = useFocusTransition(EUKARYOTA_TAXID)
  const [selectedIndex, setSelectedIndex] = useState(0)
  const parentTabRef = useRef<HTMLButtonElement>(null)
  const speciesRef = useRef<HTMLDivElement>(null)

  const focus = useMemo(
    () => getRowById(focusTaxid) ?? getEukaryotaRow(),
    [focusTaxid],
  )
  const parent = useMemo(() => getParentBookmark(focusTaxid), [focusTaxid])
  const species = useMemo(() => getSpeciesForTaxid(focusTaxid), [focusTaxid])
  const { visible: deckChildren } = useMemo(() => getChildDeck(focusTaxid), [focusTaxid])

  useEffect(() => {
    setSelectedIndex(0)
  }, [focusTaxid])

  useEffect(() => {
    setSelectedIndex((i) => clampIndex(i, deckChildren.length))
  }, [deckChildren.length])

  const drill = useCallback(
    (row: TaxonRollup, sourceEl: HTMLButtonElement | null) => {
      navigate(row.taxid, "drill", {
        sourceEl,
        targetEl: heroRef.current,
        row,
      })
    },
    [navigate, heroRef],
  )

  const ascend = useCallback(
    (parentRow: TaxonRollup, sourceEl: HTMLButtonElement) => {
      navigate(parentRow.taxid, "ascend", {
        sourceEl,
        targetEl: heroRef.current,
        row: parentRow,
      })
    },
    [navigate, heroRef],
  )

  const ascendKeyboard = useCallback(() => {
    if (!parent) return
    const el = parentTabRef.current
    if (el && el.getBoundingClientRect().width > 0) {
      ascend(parent, el)
    } else {
      navigate(parent.taxid, "ascend", { row: parent })
    }
  }, [ascend, navigate, parent])

  const jump = useCallback(
    (taxid: number) => {
      navigate(taxid, "jump")
    },
    [navigate],
  )

  const jumpToGenus = useCallback(() => {
    const taxid = getSpecimenGenusTaxid()
    navigate(taxid, "jump")
    requestAnimationFrame(() => {
      speciesRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" })
    })
  }, [navigate])

  useConceptKeyboard({
    enabled: !isBusy,
    onEscape: ascendKeyboard,
    onArrowLeft: ascendKeyboard,
    onArrowUp: () => setSelectedIndex((i) => clampIndex(i - 1, deckChildren.length)),
    onArrowDown: () => setSelectedIndex((i) => clampIndex(i + 1, deckChildren.length)),
    onEnter: () => {
      const row = deckChildren[selectedIndex]
      if (!row) return
      const el = document.querySelector(
        `[data-focus-card="${row.taxid}"]`,
      ) as HTMLButtonElement | null
      drill(row, el)
    },
  })

  const slice = getSpecimenSlice()

  const centerColumn = (
    <div className="flex min-h-0 min-w-0 flex-col gap-4 overflow-y-auto overflow-x-hidden pr-1">
      <FocusHero row={focus} heroRef={heroRef} hidden={heroHidden} />
      <div ref={speciesRef}>
        <FocusSpeciesList species={species} genusName={slice.genus_name} />
      </div>
    </div>
  )

  const childColumn = (
    <ChildColumn
      focus={focus}
      focusTaxid={focusTaxid}
      selectedIndex={selectedIndex}
      onSelectIndex={setSelectedIndex}
      onDrill={drill}
      isBusy={isBusy}
    />
  )

  return (
    <FocusStackShell
      focusRow={focus}
      headerExtra={
        <>
          <Link
            href={`/taxonomy/atlas?view=scatter`}
            className={cn(buttonVariants({ variant: "outline", size: "sm" }))}
          >
            Explore
          </Link>
          <Button variant="secondary" size="sm" disabled={isBusy} onClick={jumpToGenus}>
            Jump to {slice.genus_name}
          </Button>
        </>
      }
    >
      <FocusStackLayout
        isBusy={isBusy}
        mobileNav={
          <div className="flex min-w-0 flex-col gap-2 md:hidden">
            <MobileAncestorBar focusTaxid={focusTaxid} onJump={jump} disabled={isBusy} />
            <ParentBookmark
              focusTaxid={focusTaxid}
              variant="horizontal"
              tabRef={parentTabRef}
              disabled={isBusy}
              onAscend={ascend}
            />
          </div>
        }
        left={
          <LeftSpineColumn
            focusTaxid={focusTaxid}
            onJump={jump}
            onAscend={ascend}
            parentTabRef={parentTabRef}
            disabled={isBusy}
          />
        }
        center={centerColumn}
        right={childColumn}
      />
    </FocusStackShell>
  )
}

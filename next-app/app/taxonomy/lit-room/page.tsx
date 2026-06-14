"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import Link from "next/link"
import {
  EUKARYOTA_TAXID,
  getEukaryotaRow,
  getRowById,
  getSpeciesForTaxid,
  getSpecimenGenusTaxid,
  getSpecimenSlice,
} from "@/lib/taxonomy-mock"
import type { SpecimenSpeciesRow, TaxonRollup } from "@/lib/taxonomy-mock/types"
import { getChildDeck, getParentBookmark } from "@/lib/taxonomy/focus-nav"
import { getLitRoomMode } from "@/lib/taxonomy/lit-room"
import { LitRoomShell } from "@/components/taxonomy/lit-room/LitRoomShell"
import { LitRoomStage } from "@/components/taxonomy/lit-room/LitRoomStage"
import { ChamberStack } from "@/components/taxonomy/lit-room/ChamberStack"
import { AncestryFilament } from "@/components/taxonomy/lit-room/AncestryFilament"
import { ParentAscendCard } from "@/components/taxonomy/lit-room/ParentAscendCard"
import { ChildThreshold } from "@/components/taxonomy/lit-room/ChildThreshold"
import { FloorMosaic } from "@/components/taxonomy/lit-room/FloorMosaic"
import { TileLevitation } from "@/components/taxonomy/lit-room/TileLevitation"
import { specimenToLevitationDetail } from "@/components/taxonomy/lit-room/lit-room-utils"
import { useChamberMotion } from "@/hooks/useChamberMotion"
import { useLitRoomKeyboard } from "@/hooks/useLitRoomKeyboard"
import "@/components/taxonomy/lit-room/lit-room-tokens.css"
import "@/components/taxonomy/lit-room/chamber-motion.css"

function clampIndex(index: number, length: number): number {
  if (length <= 0) return 0
  return Math.max(0, Math.min(index, length - 1))
}

function useMdUp(): boolean {
  const [mdUp, setMdUp] = useState(false)
  useEffect(() => {
    const mq = window.matchMedia("(min-width: 768px)")
    const update = () => setMdUp(mq.matches)
    update()
    mq.addEventListener("change", update)
    return () => mq.removeEventListener("change", update)
  }, [])
  return mdUp
}

function resolveMorphSource(button: HTMLButtonElement | null): HTMLElement | null {
  if (!button) return null
  return button.querySelector<HTMLElement>(".clade-card-shell") ?? button
}

export default function TaxonomyLitRoomPage() {
  const {
    focusTaxid,
    motionPhase,
    motionDirection,
    sourceTaxid,
    heroVisible,
    chamberEclipsed,
    detailsCardRef,
    isBusy,
    navigate,
    animateLevitate,
  } = useChamberMotion(EUKARYOTA_TAXID)

  const [thresholdIndex, setThresholdIndex] = useState(0)
  const [floorIndex, setFloorIndex] = useState(0)
  const [levitatedRow, setLevitatedRow] = useState<SpecimenSpeciesRow | null>(null)
  const [levitationOpen, setLevitationOpen] = useState(false)
  const parentRef = useRef<HTMLButtonElement>(null)
  const levitationRef = useRef<HTMLDivElement>(null)

  const focus = useMemo(
    () => getRowById(focusTaxid) ?? getEukaryotaRow(),
    [focusTaxid],
  )
  const species = useMemo(() => getSpeciesForTaxid(focusTaxid), [focusTaxid])
  const mode = useMemo(() => getLitRoomMode(focusTaxid), [focusTaxid])
  const { visible: thresholdChildren } = useMemo(() => getChildDeck(focusTaxid), [focusTaxid])
  const slice = getSpecimenSlice()
  const mdUp = useMdUp()
  const navActive = mode.showFloor ? "floor" : "threshold"
  const navLength = navActive === "floor" ? species.length : thresholdChildren.length

  useEffect(() => {
    setThresholdIndex(0)
    setFloorIndex(0)
    setLevitatedRow(null)
    setLevitationOpen(false)
  }, [focusTaxid])

  useEffect(() => {
    setThresholdIndex((i) => clampIndex(i, thresholdChildren.length))
  }, [thresholdChildren.length])

  useEffect(() => {
    setFloorIndex((i) => clampIndex(i, species.length))
  }, [species.length])

  const drill = useCallback(
    (row: TaxonRollup, sourceEl: HTMLButtonElement | null) => {
      setLevitationOpen(false)
      setLevitatedRow(null)
      navigate(row.taxid, "drill", {
        sourceEl: resolveMorphSource(sourceEl),
        targetEl: detailsCardRef.current,
        row,
      })
    },
    [navigate, detailsCardRef],
  )

  const ascend = useCallback(
    (parentRow: TaxonRollup, sourceEl: HTMLButtonElement) => {
      setLevitationOpen(false)
      setLevitatedRow(null)
      navigate(parentRow.taxid, "ascend", {
        sourceEl: resolveMorphSource(sourceEl),
        targetEl: detailsCardRef.current,
        row: parentRow,
      })
    },
    [navigate, detailsCardRef],
  )

  const ascendKeyboard = useCallback(() => {
    if (levitationOpen) {
      setLevitationOpen(false)
      setLevitatedRow(null)
      return
    }
    const parentRow = getParentBookmark(focusTaxid)
    if (!parentRow) return
    const el = parentRef.current
    if (el && el.getBoundingClientRect().width > 0) {
      ascend(parentRow, el)
    } else {
      navigate(parentRow.taxid, "ascend", { row: parentRow })
    }
  }, [ascend, navigate, focusTaxid, levitationOpen])

  const jump = useCallback(
    (taxid: number) => {
      setLevitationOpen(false)
      setLevitatedRow(null)
      navigate(taxid, "jump")
    },
    [navigate],
  )

  const jumpToGenus = useCallback(() => {
    navigate(getSpecimenGenusTaxid(), "jump")
  }, [navigate])

  const levitateStone = useCallback(
    async (row: SpecimenSpeciesRow, sourceEl: HTMLButtonElement | null) => {
      setLevitatedRow(row)
      await animateLevitate({
        sourceEl,
        targetEl: levitationRef.current,
        html: `<div class="p-2"><p class="lit-scientific text-sm">${row.scientific_name}</p></div>`,
      })
      setLevitationOpen(true)
    },
    [animateLevitate],
  )

  const cycleThreshold = useCallback(
    (delta: number) => {
      if (navActive === "floor") {
        setFloorIndex((i) => clampIndex(i + delta, species.length))
      } else {
        setThresholdIndex((i) => clampIndex(i + delta, thresholdChildren.length))
      }
    },
    [navActive, species.length, thresholdChildren.length],
  )

  useLitRoomKeyboard({
    enabled: !isBusy,
    onEscape: ascendKeyboard,
    onArrowLeft: () => {
      if (levitationOpen) return
      cycleThreshold(-1)
    },
    onArrowRight: () => {
      if (levitationOpen) return
      cycleThreshold(1)
    },
    onArrowUp: () => {
      if (levitationOpen) return
      cycleThreshold(-1)
    },
    onArrowDown: () => {
      if (levitationOpen) return
      cycleThreshold(1)
    },
    onEnter: () => {
      if (navActive === "floor") {
        const row = species[floorIndex]
        if (!row) return
        const el = document.querySelector(
          `[data-species-tile="${row.taxid}"]`,
        ) as HTMLButtonElement | null
        void levitateStone(row, el)
        return
      }
      const row = thresholdChildren[thresholdIndex]
      if (!row) return
      const el = document.querySelector(
        `[data-doorway="${row.taxid}"]`,
      ) as HTMLButtonElement | null
      drill(row, el)
    },
  })

  const mosaicProps = {
    species,
    genusName: slice.genus_name,
    selectedIndex: floorIndex,
    onSelectIndex: setFloorIndex,
    onLevitate: (row: SpecimenSpeciesRow, el: HTMLButtonElement | null) => void levitateStone(row, el),
    isBusy,
  } as const

  const parentTaxid = getParentBookmark(focusTaxid)?.taxid ?? null

  const chamber = (
    <ChamberStack
      row={focus}
      mode={mode}
      detailsRef={detailsCardRef}
      motionPhase={motionPhase}
      motionDirection={motionDirection}
      heroVisible={heroVisible}
      eclipsed={chamberEclipsed || levitationOpen}
      parent={
        <ParentAscendCard
          ref={parentRef}
          focusTaxid={focusTaxid}
          onAscend={ascend}
          disabled={isBusy}
          isMorphSource={sourceTaxid != null && sourceTaxid === parentTaxid}
        />
      }
      floor={mode.showFloor && mdUp ? <FloorMosaic {...mosaicProps} /> : undefined}
    >
      {mode.showDoorways && (
        <ChildThreshold
          focus={focus}
          focusTaxid={focusTaxid}
          selectedIndex={thresholdIndex}
          onSelectIndex={setThresholdIndex}
          onDrill={drill}
          isBusy={isBusy}
          motionPhase={motionPhase}
          sourceTaxid={sourceTaxid}
        />
      )}
    </ChamberStack>
  )

  const levitationDetail = levitatedRow
    ? specimenToLevitationDetail(levitatedRow, slice.genus_name)
    : null

  return (
    <LitRoomShell
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
            disabled={isBusy}
            onClick={jumpToGenus}
            className="inline-flex h-8 items-center rounded-md bg-primary/15 px-3 text-sm text-primary hover:bg-primary/25 disabled:opacity-50"
          >
            Jump to {slice.genus_name}
          </button>
        </>
      }
    >
      <LitRoomStage
        isBusy={isBusy}
        mobileNav={
          <div className="flex min-w-0 flex-col gap-2">
            <AncestryFilament
              focusTaxid={focusTaxid}
              onJump={jump}
              disabled={isBusy}
              variant="horizontal"
            />
            <ParentAscendCard
              ref={parentRef}
              focusTaxid={focusTaxid}
              onAscend={ascend}
              disabled={isBusy}
              variant="compact"
              isMorphSource={sourceTaxid != null && sourceTaxid === parentTaxid}
            />
          </div>
        }
        filament={
          <AncestryFilament focusTaxid={focusTaxid} onJump={jump} disabled={isBusy} />
        }
        chamber={
          <>
            {chamber}
            {mode.showFloor && !mdUp && (
              <div className="mt-3 min-w-0 md:hidden">
                <FloorMosaic {...mosaicProps} />
              </div>
            )}
          </>
        }
      />
      <TileLevitation
        detail={levitationDetail}
        row={levitatedRow}
        open={levitationOpen}
        onClose={() => {
          setLevitationOpen(false)
          setLevitatedRow(null)
        }}
        levitationRef={levitationRef}
      />
    </LitRoomShell>
  )
}

"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { flushSync } from "react-dom"
import { cladeCardSnapshotHtml } from "@/components/taxonomy/lit-room/lit-room-utils"
import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import {
  fadeOverlay,
  flipMorph,
  getCladeShellRect,
  stoneLevitateMorph,
  waitDoubleRaf,
} from "@/lib/taxonomy/lit-room-flip"
import { cn } from "@/lib/utils"

export type ChamberMotionDirection = "drill" | "ascend" | "jump" | "levitate"
export type ChamberMotionPhase = "idle" | "prepare" | "morph" | "commit" | "settle"

const SETTLE_MS = 650

function prefersReducedMotion(): boolean {
  if (typeof window === "undefined") return false
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches
}

function supportsViewTransition(): boolean {
  return typeof document !== "undefined" && "startViewTransition" in document
}

function resetMotionState(setters: {
  setMotionPhase: (p: ChamberMotionPhase) => void
  setMotionDirection: (d: ChamberMotionDirection | null) => void
  setSourceTaxid: (t: number | null) => void
  setHeroVisible: (v: boolean) => void
}) {
  setters.setMotionPhase("idle")
  setters.setMotionDirection(null)
  setters.setSourceTaxid(null)
  setters.setHeroVisible(true)
}

export function useChamberMotion(initialTaxid: number) {
  const [focusTaxid, setFocusTaxid] = useState(initialTaxid)
  const [motionPhase, setMotionPhase] = useState<ChamberMotionPhase>("idle")
  const [motionDirection, setMotionDirection] = useState<ChamberMotionDirection | null>(null)
  const [sourceTaxid, setSourceTaxid] = useState<number | null>(null)
  const [heroVisible, setHeroVisible] = useState(true)
  const [chamberEclipsed, setChamberEclipsed] = useState(false)
  const detailsCardRef = useRef<HTMLDivElement>(null)
  const busyRef = useRef(false)

  const navigate = useCallback(
    async (
      targetTaxid: number,
      direction: Exclude<ChamberMotionDirection, "levitate">,
      opts?: {
        sourceEl?: HTMLElement | null
        targetEl?: HTMLElement | null
        row?: TaxonRollup
      },
    ) => {
      if (busyRef.current || targetTaxid === focusTaxid) return
      busyRef.current = true
      setMotionPhase("prepare")
      setMotionDirection(direction)

      const commit = () => {
        flushSync(() => setFocusTaxid(targetTaxid))
      }

      const finish = () => {
        resetMotionState({
          setMotionPhase,
          setMotionDirection,
          setSourceTaxid,
          setHeroVisible,
        })
        busyRef.current = false
      }

      try {
        if (prefersReducedMotion()) {
          commit()
          return
        }

        const detailsEl = opts?.targetEl ?? detailsCardRef.current

        if (direction === "jump") {
          if (supportsViewTransition()) {
            await (
              document as Document & {
                startViewTransition: (cb: () => void) => { finished: Promise<void> }
              }
            ).startViewTransition(commit).finished
          } else {
            commit()
          }
          return
        }

        setSourceTaxid(opts?.row?.taxid ?? null)
        setHeroVisible(false)

        await waitDoubleRaf()

        const sourceEl = opts?.sourceEl
        const sourceRect = sourceEl ? getCladeShellRect(sourceEl) : null
        const detailsRect = detailsEl?.getBoundingClientRect()

        if (
          sourceRect &&
          detailsRect &&
          sourceEl &&
          detailsRect.width > 0 &&
          sourceRect.width > 0 &&
          (direction === "drill" || direction === "ascend")
        ) {
          setMotionPhase("morph")

          const html = opts?.row
            ? cladeCardSnapshotHtml(opts.row)
            : `<div class="p-3"><p class="text-xs">${sourceEl.textContent?.slice(0, 60) ?? ""}</p></div>`

          const overlay = await flipMorph({
            fromRect: sourceRect,
            toRect: detailsRect,
            html,
            className: cn(
              "clade-morph-overlay rounded-xl border border-primary/30 bg-card/95 shadow-2xl backdrop-blur-sm",
              direction === "drill" ? "is-drill" : "is-ascend",
            ),
            easing:
              direction === "drill"
                ? "cubic-bezier(0.22, 1.1, 0.36, 1)"
                : "cubic-bezier(0.34, 1.2, 0.64, 1)",
            keepOnComplete: true,
          })

          setMotionPhase("commit")
          commit()

          setMotionPhase("settle")
          setHeroVisible(true)

          if (overlay) {
            await fadeOverlay(overlay, 0, 120)
            overlay.remove()
          }

          await new Promise((r) => setTimeout(r, SETTLE_MS))
          return
        }

        setHeroVisible(false)

        if (supportsViewTransition()) {
          await (
            document as Document & {
              startViewTransition: (cb: () => void) => { finished: Promise<void> }
            }
          ).startViewTransition(commit).finished
        } else {
          await new Promise((r) => setTimeout(r, 100))
          commit()
        }

        setMotionPhase("settle")
        setHeroVisible(true)
        await new Promise((r) => setTimeout(r, SETTLE_MS))
      } finally {
        finish()
      }
    },
    [focusTaxid],
  )

  const animateLevitate = useCallback(
    async (opts: {
      sourceEl?: HTMLElement | null
      targetEl?: HTMLElement | null
      html?: string
    }) => {
      if (busyRef.current) return
      busyRef.current = true
      setMotionDirection("levitate")
      setMotionPhase("prepare")
      setChamberEclipsed(true)

      try {
        if (prefersReducedMotion()) return

        await waitDoubleRaf()
        const sourceEl = opts.sourceEl
        const targetEl = opts.targetEl
        const sourceRect = sourceEl?.getBoundingClientRect()
        const targetRect = targetEl?.getBoundingClientRect()

        if (sourceRect && targetRect && sourceEl && sourceRect.width > 0) {
          setMotionPhase("morph")
          const html =
            opts.html ??
            `<div class="p-2"><p class="text-sm">${sourceEl.textContent?.slice(0, 80) ?? ""}</p></div>`
          await stoneLevitateMorph(sourceRect, targetRect, html)
        }
      } finally {
        setMotionPhase("idle")
        setMotionDirection(null)
        setChamberEclipsed(false)
        busyRef.current = false
      }
    },
    [],
  )

  useEffect(() => {
    const title = detailsCardRef.current?.querySelector("[data-lit-chamber-title]")
    if (motionPhase === "idle" && title instanceof HTMLElement) {
      title.focus({ preventScroll: true })
    }
  }, [focusTaxid, motionPhase])

  return {
    focusTaxid,
    motionPhase,
    motionDirection,
    sourceTaxid,
    heroVisible,
    chamberEclipsed,
    detailsCardRef,
    isBusy: motionPhase !== "idle",
    navigate,
    animateLevitate,
  }
}

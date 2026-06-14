"use client"

import { useCallback, useEffect, useRef, useState } from "react"
import { flushSync } from "react-dom"
import { cardSnapshotHtml } from "@/components/taxonomy/focus/ChildOverviewCard"
import type { TaxonRollup } from "@/lib/taxonomy-mock/types"

export type FocusTransitionDirection = "drill" | "ascend" | "jump"

function prefersReducedMotion(): boolean {
  if (typeof window === "undefined") return false
  return window.matchMedia("(prefers-reduced-motion: reduce)").matches
}

function supportsViewTransition(): boolean {
  return typeof document !== "undefined" && "startViewTransition" in document
}

function waitDoubleRaf(): Promise<void> {
  return new Promise((resolve) => {
    requestAnimationFrame(() => requestAnimationFrame(() => resolve()))
  })
}

function runFlip(fromRect: DOMRect, toRect: DOMRect, html: string): Promise<void> {
  return new Promise((resolve) => {
    const el = document.createElement("div")
    el.className = "focus-flip-overlay rounded-lg border border-border bg-card shadow-lg"
    el.style.left = `${fromRect.left}px`
    el.style.top = `${fromRect.top}px`
    el.style.width = `${fromRect.width}px`
    el.style.height = `${fromRect.height}px`
    el.style.transformOrigin = "top left"
    el.innerHTML = html

    const dx = toRect.left - fromRect.left
    const dy = toRect.top - fromRect.top
    const sx = fromRect.width > 0 ? toRect.width / fromRect.width : 1
    const sy = fromRect.height > 0 ? toRect.height / fromRect.height : 1

    document.body.appendChild(el)

    requestAnimationFrame(() => {
      el.style.transform = `translate(${dx}px, ${dy}px) scale(${sx}, ${sy})`
    })

    const finish = () => {
      el.remove()
      resolve()
    }
    el.addEventListener("transitionend", (ev) => {
      if (ev.propertyName === "transform") finish()
    }, { once: true })
    window.setTimeout(finish, 400)
  })
}

function snapshotFromElement(el: HTMLElement, row?: TaxonRollup): string {
  if (row) return cardSnapshotHtml(row)
  const name = el.querySelector(".taxon-name")?.textContent ?? el.textContent ?? ""
  return `<div class="p-2"><p class="text-sm font-medium">${name}</p></div>`
}

export function useFocusTransition(initialTaxid: number) {
  const [focusTaxid, setFocusTaxid] = useState(initialTaxid)
  const [phase, setPhase] = useState<"idle" | FocusTransitionDirection>("idle")
  const [heroHidden, setHeroHidden] = useState(false)
  const heroRef = useRef<HTMLDivElement>(null)
  const busyRef = useRef(false)

  const navigate = useCallback(
    async (
      targetTaxid: number,
      direction: FocusTransitionDirection,
      opts?: {
        sourceEl?: HTMLElement | null
        targetEl?: HTMLElement | null
        row?: TaxonRollup
      },
    ) => {
      if (busyRef.current || targetTaxid === focusTaxid) return
      busyRef.current = true
      setPhase(direction)

      const commit = () => {
        flushSync(() => setFocusTaxid(targetTaxid))
      }

      try {
        if (prefersReducedMotion()) {
          commit()
          return
        }

        const heroEl = opts?.targetEl ?? heroRef.current

        if (direction === "jump") {
          setHeroHidden(true)
          await new Promise((r) => setTimeout(r, 80))
          if (supportsViewTransition()) {
            await (
              document as Document & {
                startViewTransition: (cb: () => void) => { finished: Promise<void> }
              }
            ).startViewTransition(commit).finished
          } else {
            commit()
          }
          setHeroHidden(false)
          return
        }

        await waitDoubleRaf()

        const sourceEl = opts?.sourceEl
        const heroRect = heroEl?.getBoundingClientRect()
        const sourceRect = sourceEl?.getBoundingClientRect()

        if (heroRect && sourceRect && sourceEl && heroRect.width > 0 && sourceRect.width > 0) {
          setHeroHidden(true)
          const html = opts?.row
            ? cardSnapshotHtml(opts.row)
            : snapshotFromElement(sourceEl)
          await runFlip(sourceRect, heroRect, html)
          commit()
          setHeroHidden(false)
          return
        }

        setHeroHidden(true)
        if (supportsViewTransition()) {
          await (
            document as Document & {
              startViewTransition: (cb: () => void) => { finished: Promise<void> }
            }
          ).startViewTransition(commit).finished
        } else {
          await new Promise((r) => setTimeout(r, 120))
          commit()
        }
        setHeroHidden(false)
      } finally {
        setPhase("idle")
        setHeroHidden(false)
        busyRef.current = false
      }
    },
    [focusTaxid],
  )

  useEffect(() => {
    const title = heroRef.current?.querySelector("[data-focus-title]")
    if (phase === "idle" && title instanceof HTMLElement) {
      title.focus({ preventScroll: true })
    }
  }, [focusTaxid, phase])

  return {
    focusTaxid,
    phase,
    heroHidden,
    heroRef,
    isBusy: phase !== "idle",
    navigate,
  }
}

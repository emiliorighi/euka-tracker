"use client"

import { useEffect, useRef, useState } from "react"
import { resolveZoomTarget } from "@/lib/scatter/centroids"
import { EUKARYOTA_TAXID, SCATTER_TILE_URL } from "@/lib/scatter/config"
import {
  type CladeBackgroundOptions,
  type ScatterEncoding,
} from "@/lib/scatter/encoding"
import type { ScatterLayoutId } from "@/lib/scatter/layouts"
import { installRootExtentFix, verifyTileSource } from "@/lib/scatter/tiles"

const ENCODING_TRANSITION_MS = 500
const MIN_CONTAINER_SIZE = 64

type ScatterZoomBbox = {
  x: [number, number]
  y: [number, number]
}

type ScatterplotInstance = {
  plotAPI: (opts: Record<string, unknown>) => Promise<void>
  destroy: () => void
  ready: Promise<void>
  click_function?: (datum: Record<string, unknown>) => void
  tooltip_html?: (datum: Record<string, unknown>) => string
}

type ScatterDatum = {
  taxid?: number
  scientific_name?: string
  phylum_name?: string
}

function hasSize(el: HTMLElement): boolean {
  const { width, height } = el.getBoundingClientRect()
  return width >= MIN_CONTAINER_SIZE && height >= MIN_CONTAINER_SIZE
}

function waitForSize(el: HTMLElement, signal: AbortSignal): Promise<void> {
  return new Promise((resolve, reject) => {
    if (hasSize(el)) {
      resolve()
      return
    }

    const onAbort = () => {
      ro.disconnect()
      reject(new DOMException("Aborted", "AbortError"))
    }

    const ro = new ResizeObserver(() => {
      if (hasSize(el)) {
        ro.disconnect()
        signal.removeEventListener("abort", onAbort)
        resolve()
      }
    })

    ro.observe(el)
    signal.addEventListener("abort", onAbort, { once: true })
  })
}

async function applySelectionUpdate(
  plot: ScatterplotInstance,
  encoding: ScatterEncoding,
  backgroundOptions: CladeBackgroundOptions,
  bbox: ScatterZoomBbox,
  duration = ENCODING_TRANSITION_MS,
): Promise<void> {
  await plot.plotAPI({
    duration,
    encoding,
    background_options: backgroundOptions,
    zoom: { bbox },
    zoom_align: "center",
  })
}

async function applyEncoding(
  plot: ScatterplotInstance,
  encoding: ScatterEncoding,
  backgroundOptions: CladeBackgroundOptions,
  duration = ENCODING_TRANSITION_MS,
): Promise<void> {
  await plot.plotAPI({
    duration,
    encoding,
    background_options: backgroundOptions,
  })
}

function attachPlotHandlers(plot: ScatterplotInstance): void {
  plot.click_function = (datum) => {
    window.dispatchEvent(
      new CustomEvent("species-click", { detail: datum as ScatterDatum }),
    )
  }
  plot.tooltip_html = (datum) => {
    const d = datum as ScatterDatum
    const name = d.scientific_name?.trim()
    const taxid = d.taxid
    const phylum = d.phylum_name?.trim()
    const parts: string[] = []
    if (name) parts.push(`<b>${name}</b>`)
    if (phylum) parts.push(`<span>${phylum}</span>`)
    parts.push(`<span>taxid ${taxid ?? "—"}</span>`)
    return parts.join("<br/>")
  }
}

type Props = {
  sourceUrl?: string
  encoding: ScatterEncoding
  encodingKey: string
  backgroundOptions: CladeBackgroundOptions
  focusTaxid: number
  focusDepth: number
  focusKey: string
  layout: ScatterLayoutId
}

export function SpeciesScatterPlot({
  sourceUrl = SCATTER_TILE_URL,
  encoding,
  encodingKey,
  backgroundOptions,
  focusTaxid,
  focusDepth,
  focusKey,
  layout,
}: Props) {
  const containerRef = useRef<HTMLDivElement>(null)
  const plotRef = useRef<ScatterplotInstance | null>(null)
  const readyRef = useRef(false)
  const skipInitialZoomRef = useRef(true)
  const encodingRef = useRef(encoding)
  const backgroundOptionsRef = useRef(backgroundOptions)
  const [initError, setInitError] = useState<string | null>(null)
  const [plotReadyTick, setPlotReadyTick] = useState(0)

  encodingRef.current = encoding
  backgroundOptionsRef.current = backgroundOptions

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    let plot: ScatterplotInstance | null = null
    let cancelled = false
    const abort = new AbortController()
    readyRef.current = false
    setInitError(null)

    ;(async () => {
      try {
        await waitForSize(container, abort.signal)
        if (cancelled) return

        await verifyTileSource(sourceUrl)
        if (cancelled) return

        const mod = await import("deepscatter")
        if (cancelled) return

        const Scatterplot = (mod.default ?? mod.Scatterplot) as new (
          el: HTMLElement,
        ) => ScatterplotInstance

        installRootExtentFix(
          Scatterplot as unknown as Parameters<typeof installRootExtentFix>[0],
        )

        plot = new Scatterplot(container)
        plotRef.current = plot
        attachPlotHandlers(plot)

        const baseEncoding: ScatterEncoding = {
          x: encodingRef.current.x,
          y: encodingRef.current.y,
          color: encodingRef.current.color,
        }

        await plot.plotAPI({
          source_url: sourceUrl,
          max_points: 1_000_000,
          alpha: 45,
          zoom_balance: 0.38,
          point_size: 4,
          background_color: "#0a0a0a",
          encoding: baseEncoding,
        })
        if (cancelled) return

        await plot.ready
        if (cancelled) return

        readyRef.current = true
        setPlotReadyTick((tick) => tick + 1)
        await applyEncoding(
          plot,
          encodingRef.current,
          backgroundOptionsRef.current,
          0,
        )
      } catch (error) {
        if (cancelled || readyRef.current) return
        const message =
          error instanceof Error ? error.message : "Failed to initialize scatter plot"
        console.error("deepscatter init failed:", error)
        setInitError(message)
      }
    })()

    return () => {
      cancelled = true
      abort.abort()
      readyRef.current = false
      plotRef.current?.destroy()
      plotRef.current = null
      plot = null
    }
  }, [sourceUrl])

  useEffect(() => {
    const plot = plotRef.current
    if (!plot || !readyRef.current) return

    if (skipInitialZoomRef.current) {
      skipInitialZoomRef.current = false
      if (focusTaxid === EUKARYOTA_TAXID || focusDepth <= 0) return
    }

    let cancelled = false

    ;(async () => {
      try {
        await plot.ready
        if (cancelled) return
        const bbox = await resolveZoomTarget(
          sourceUrl,
          focusTaxid,
          focusDepth,
          layout,
        )
        if (cancelled) return
        await applySelectionUpdate(
          plot,
          encodingRef.current,
          backgroundOptionsRef.current,
          bbox,
        )
      } catch (error) {
        console.error("deepscatter selection update failed:", error)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [focusKey, sourceUrl, focusTaxid, focusDepth, layout, plotReadyTick])

  return (
    <div
      ref={containerRef}
      className="relative h-full min-h-[16rem] w-full bg-[#0a0a0a]"
    >
      {initError ? (
        <div className="absolute inset-0 flex items-center justify-center bg-[#0a0a0a]/90 p-6 text-center">
          <p className="max-w-md text-sm text-red-300">{initError}</p>
        </div>
      ) : null}
    </div>
  )
}

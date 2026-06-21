"use client"

import { useEffect, useId, useRef, useState } from "react"
import { IUCN_CLADE_LABELS_URL } from "@/lib/iucn/config"
import {
  ensureIucnCodeColumn,
  ensureInCladeColumn,
  ensurePipelineColumns,
} from "@/lib/iucn/scatter-transforms"
import type { IucnSpeciesDatum } from "@/lib/iucn/types"
import {
  type CladeBackgroundOptions,
  inCladeTransformField,
  type ScatterEncoding,
} from "@/lib/scatter/encoding"
import type { IucnRank } from "@/lib/iucn/config"
import {
  createDeepscatterPlot,
  importDeepscatter,
  type DeepscatterPlot,
} from "@/lib/scatter/deepscatter"
import { resolveScatterSource } from "@/lib/scatter/scatter-data"
import type { TileRectangle } from "@/lib/scatter/tiles"

const ENCODING_TRANSITION_MS = 500
const MIN_CONTAINER_SIZE = 64
const MAX_POINTS = 500_000
const ZOOM_BALANCE = 0.7

type ScatterZoomController = {
  zoom_to_bbox: (corners: TileRectangle, duration?: number) => void
}

function scatterSelector(containerId: string): string {
  return `#${CSS.escape(containerId)}`
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

async function applyEncoding(
  plot: DeepscatterPlot,
  encoding: ScatterEncoding,
  backgroundOptions: CladeBackgroundOptions,
  duration = ENCODING_TRANSITION_MS,
): Promise<void> {
  await plot.plotAPI({
    duration,
    encoding,
    background_options: backgroundOptions,
    labels: CLADE_LABELS,
  })
}

async function zoomToExtent(
  plot: DeepscatterPlot,
  extent: TileRectangle,
  duration = 0,
): Promise<void> {
  const zoom = plot._zoom
  if (zoom?.zoom_to_bbox) {
    zoom.zoom_to_bbox(extent, duration)
    return
  }
  await plot.plotAPI({
    duration,
    zoom: { bbox: extent },
    zoom_align: "center",
  })
}

async function prepareDerivedColumns(
  plot: DeepscatterPlot,
  selectedRank: IucnRank | null | undefined,
  selectedTaxonName: string | null | undefined,
  selectionKey: string | null | undefined,
  options: { precomputed: boolean },
): Promise<void> {
  if (!options.precomputed) {
    await ensureIucnCodeColumn(plot)
    await ensurePipelineColumns(plot)
  }
  if (selectedRank && selectedTaxonName?.trim() && selectionKey) {
    await ensureInCladeColumn(
      plot,
      inCladeTransformField(selectionKey),
      selectedRank,
      selectedTaxonName,
    )
  }
}

function scatterTooltipHtml(datum: Record<string, unknown>): string {
  const d = datum as IucnSpeciesDatum
  const name = d.scientificName?.trim()
  const category = d.redlistCategory?.trim()
  const kingdom = d.kingdomName?.trim()
  const parts: string[] = []
  if (name) {
    parts.push(`<div style="font-weight:600;font-style:italic;color:#fafafa">${name}</div>`)
  }
  if (category) {
    parts.push(`<div style="color:#d4d4d8;margin-top:2px">${category}</div>`)
  }
  if (kingdom) {
    parts.push(`<div style="color:#a1a1aa;margin-top:2px">${kingdom}</div>`)
  }
  return `<div style="color:#f4f4f5;line-height:1.4">${parts.join("")}</div>`
}

const CLADE_LABELS = {
  url: IUCN_CLADE_LABELS_URL,
  label_field: "label",
  size_field: "labelSize",
  name: "clade_labels",
} as const

type Props = {
  encoding: ScatterEncoding
  filterKey: string
  taxonEncodingKey: string
  backgroundOptions: CladeBackgroundOptions
  selectedRank?: IucnRank | null
  selectedTaxonName?: string | null
  selectionKey?: string | null
  onSpeciesClick?: (datum: IucnSpeciesDatum) => void
}

export function SpeciesScatterPlot({
  encoding,
  filterKey,
  taxonEncodingKey,
  backgroundOptions,
  selectedRank,
  selectedTaxonName,
  selectionKey,
  onSpeciesClick,
}: Props) {
  const plotContainerId = useId().replace(/:/g, "")
  const containerRef = useRef<HTMLDivElement>(null)
  const plotRef = useRef<DeepscatterPlot | null>(null)
  const readyRef = useRef(false)
  const precomputedRef = useRef(true)
  const extentRef = useRef<TileRectangle | null>(null)
  const skipInitialEncodingTransitionRef = useRef(true)
  const encodingRef = useRef(encoding)
  const backgroundOptionsRef = useRef(backgroundOptions)
  const onSpeciesClickRef = useRef(onSpeciesClick)
  const selectionRef = useRef({ selectedRank, selectedTaxonName, selectionKey })
  const [initError, setInitError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  encodingRef.current = encoding
  backgroundOptionsRef.current = backgroundOptions
  onSpeciesClickRef.current = onSpeciesClick
  selectionRef.current = { selectedRank, selectedTaxonName, selectionKey }

  useEffect(() => {
    const container = containerRef.current
    if (!container) return

    let plot: DeepscatterPlot | null = null
    let cancelled = false
    const abort = new AbortController()
    readyRef.current = false
    setInitError(null)
    setLoading(true)

    ;(async () => {
      try {
        await waitForSize(container, abort.signal)
        if (cancelled) return

        const [source, deepscatter] = await Promise.all([
          resolveScatterSource(),
          importDeepscatter(),
        ])
        if (cancelled) return

        precomputedRef.current = source.mode === "tiles"
        extentRef.current = source.extent

        const { width, height } = container.getBoundingClientRect()
        plot = createDeepscatterPlot(
          deepscatter,
          scatterSelector(plotContainerId),
          width,
          height,
        )
        plotRef.current = plot

        plot.click_function = (datum) => {
          onSpeciesClickRef.current?.(datum as IucnSpeciesDatum)
        }
        plot.tooltip_html = scatterTooltipHtml

        const initialPlotApi: Record<string, unknown> = {
          max_points: MAX_POINTS,
          alpha: 25,
          point_size: 2,
          zoom_balance: ZOOM_BALANCE,
          background_color: "#0a0a0a",
          tooltip_opacity: 1,
          labels: CLADE_LABELS,
          encoding: {
            x: { field: "x", transform: "literal" },
            y: { field: "y", transform: "literal" },
          },
        }

        if (source.mode === "tiles") {
          initialPlotApi.source_url = source.tileUrl
        } else {
          initialPlotApi.arrow_buffer = source.buffer
        }

        await plot.plotAPI(initialPlotApi)
        if (cancelled) return

        await plot.ready
        if (cancelled) return

        const { selectedRank: rank, selectedTaxonName: name, selectionKey: key } =
          selectionRef.current
        await prepareDerivedColumns(plot, rank, name, key, {
          precomputed: precomputedRef.current,
        })
        if (cancelled) return

        await applyEncoding(
          plot,
          encodingRef.current,
          backgroundOptionsRef.current,
          0,
        )
        if (cancelled) return

        await zoomToExtent(plot, source.extent, 0)
        if (cancelled) return

        readyRef.current = true
        setLoading(false)
      } catch (error) {
        if (cancelled || readyRef.current) return
        const message =
          error instanceof Error ? error.message : "Failed to initialize scatter plot"
        console.error("deepscatter init failed:", error)
        setInitError(message)
        setLoading(false)
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
  }, [plotContainerId])

  useEffect(() => {
    const plot = plotRef.current
    if (!plot || !readyRef.current) return

    let cancelled = false

    ;(async () => {
      try {
        await prepareDerivedColumns(
          plot,
          selectedRank,
          selectedTaxonName,
          selectionKey,
          { precomputed: precomputedRef.current },
        )
        if (cancelled) return
        await plot.ready
        if (cancelled) return

        const duration = skipInitialEncodingTransitionRef.current ? 0 : ENCODING_TRANSITION_MS
        skipInitialEncodingTransitionRef.current = false
        await applyEncoding(
          plot,
          encodingRef.current,
          backgroundOptionsRef.current,
          duration,
        )
      } catch (error) {
        const message =
          error instanceof Error ? error.message : "Scatter encoding update failed"
        console.error("deepscatter taxon encoding update failed:", error)
        setInitError(message)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [taxonEncodingKey])

  useEffect(() => {
    const plot = plotRef.current
    if (!plot || !readyRef.current) return

    let cancelled = false

    ;(async () => {
      try {
        await applyEncoding(
          plot,
          encodingRef.current,
          backgroundOptionsRef.current,
          0,
        )
      } catch (error) {
        if (cancelled) return
        const message =
          error instanceof Error ? error.message : "Scatter filter update failed"
        console.error("deepscatter filter update failed:", error)
        setInitError(message)
      }
    })()

    return () => {
      cancelled = true
    }
  }, [filterKey])

  return (
    <div
      id={plotContainerId}
      ref={containerRef}
      className="relative h-full min-h-[16rem] w-full bg-[#0a0a0a]"
    >
      {loading && !initError ? (
        <div className="pointer-events-none absolute inset-0 flex items-center justify-center text-sm text-muted-foreground">
          Loading scatter…
        </div>
      ) : null}
      {initError ? (
        <div className="absolute inset-0 flex items-center justify-center bg-[#0a0a0a]/90 p-6 text-center">
          <p className="max-w-md text-sm text-red-300">{initError}</p>
        </div>
      ) : null}
    </div>
  )
}

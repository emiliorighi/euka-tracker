"use client"

import { useCallback, useEffect, useMemo, useRef, useState } from "react"
import { useVirtualizer } from "@tanstack/react-virtual"
import { ChevronRight, Loader2 } from "lucide-react"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { cn } from "@/lib/utils"
import {
  getChildren,
  type IucnTaxonNode,
  type SelectedTaxon,
  useIucnTreeStore,
} from "@/lib/iucn/tree-store"

const ROW_HEIGHT = 32

type FlatRow = {
  key: string
  node: IucnTaxonNode
  depth: number
  hasChildren: boolean
  expanded: boolean
}

function TreeBody({
  selectedTaxon,
  onSelectTaxon,
}: {
  selectedTaxon: SelectedTaxon | null
  onSelectTaxon: (taxon: SelectedTaxon) => void
}) {
  const { status, index, load } = useIucnTreeStore()
  const [expanded, setExpanded] = useState<Set<string>>(() => new Set())

  useEffect(() => {
    if (status === "idle") void load()
  }, [status, load])

  const toggleExpanded = useCallback((taxonKey: string) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(taxonKey)) next.delete(taxonKey)
      else next.add(taxonKey)
      return next
    })
  }, [])

  const flatRows = useMemo(() => {
    if (!index) return [] as FlatRow[]
    const rows: FlatRow[] = []

    const walk = (parentKey: string | null, depth: number) => {
      const nodes = parentKey
        ? getChildren(index, parentKey)
        : index.roots
            .map((key) => index.rowByKey.get(key))
            .filter((node): node is IucnTaxonNode => node != null)
      for (const node of nodes) {
        const childKeys = index.childrenByParent.get(node.taxonKey) ?? []
        const hasChildren = childKeys.length > 0
        const isExpanded = expanded.has(node.taxonKey)
        rows.push({
          key: node.taxonKey,
          node,
          depth,
          hasChildren,
          expanded: isExpanded,
        })
        if (hasChildren && isExpanded) {
          walk(node.taxonKey, depth + 1)
        }
      }
    }

    walk(null, 0)
    return rows
  }, [index, expanded])

  const scrollRef = useRef<HTMLDivElement>(null)

  const virtualizer = useVirtualizer({
    count: flatRows.length,
    getScrollElement: () => scrollRef.current,
    estimateSize: () => ROW_HEIGHT,
    overscan: 8,
  })

  if (status === "loading") {
    return (
      <div className="flex flex-1 items-center justify-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="size-4 animate-spin" />
        Loading tree…
      </div>
    )
  }

  if (status === "error") {
    return (
      <div className="flex flex-1 items-center p-4 text-sm text-red-300">
        Failed to load taxon rollups.
      </div>
    )
  }

  return (
    <div ref={scrollRef} className="min-h-0 flex-1 overflow-y-auto">
      <div
        style={{
          height: `${virtualizer.getTotalSize()}px`,
          width: "100%",
          position: "relative",
        }}
      >
        {virtualizer.getVirtualItems().map((virtualRow) => {
          const row = flatRows[virtualRow.index]
          if (!row) return null
          const selected = selectedTaxon?.taxonKey === row.node.taxonKey
          return (
            <div
              key={row.key}
              style={{
                position: "absolute",
                top: 0,
                left: 0,
                width: "100%",
                height: `${virtualRow.size}px`,
                transform: `translateY(${virtualRow.start}px)`,
              }}
              className="px-1"
            >
              <div
                className={cn(
                  "flex h-8 items-center gap-1 rounded-md pr-2 text-sm",
                  selected ? "bg-primary/15 text-foreground" : "hover:bg-secondary/60",
                )}
                style={{ paddingLeft: `${8 + row.depth * 14}px` }}
              >
                {row.hasChildren ? (
                  <button
                    type="button"
                    aria-label={row.expanded ? "Collapse" : "Expand"}
                    onClick={() => toggleExpanded(row.node.taxonKey)}
                    className="flex size-5 shrink-0 items-center justify-center rounded hover:bg-secondary"
                  >
                    <ChevronRight
                      className={cn(
                        "size-3.5 text-muted-foreground transition-transform",
                        row.expanded && "rotate-90",
                      )}
                    />
                  </button>
                ) : (
                  <span className="size-5 shrink-0" />
                )}
                <button
                  type="button"
                  className="flex min-w-0 flex-1 items-baseline gap-2 text-left"
                  onClick={() =>
                    onSelectTaxon({
                      taxonKey: row.node.taxonKey,
                      taxonName: row.node.taxonName,
                      rank: row.node.rank,
                    })
                  }
                >
                  <span className="truncate font-medium italic">{row.node.taxonName}</span>
                  <span className="shrink-0 text-[10px] uppercase tracking-wide text-muted-foreground">
                    {row.node.rank}
                  </span>
                  <span className="ml-auto shrink-0 tabular-nums text-xs text-muted-foreground">
                    {row.node.speciesCountTotal.toLocaleString()}
                  </span>
                </button>
              </div>
            </div>
          )
        })}
      </div>
    </div>
  )
}

type Props = {
  open: boolean
  onOpenChange: (open: boolean) => void
  selectedTaxon: SelectedTaxon | null
  onSelectTaxon: (taxon: SelectedTaxon) => void
}

export function TaxonTreeSheet({
  open,
  onOpenChange,
  selectedTaxon,
  onSelectTaxon,
}: Props) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange} modal={false}>
      <SheetContent
        side="left"
        modal={false}
        inset
        className="flex w-full gap-0 overflow-hidden p-0 sm:max-w-md md:max-w-lg"
      >
        <SheetHeader className="shrink-0 border-b border-border px-4 py-3">
          <SheetTitle className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
            Taxonomy
          </SheetTitle>
        </SheetHeader>
        <TreeBody selectedTaxon={selectedTaxon} onSelectTaxon={onSelectTaxon} />
      </SheetContent>
    </Sheet>
  )
}

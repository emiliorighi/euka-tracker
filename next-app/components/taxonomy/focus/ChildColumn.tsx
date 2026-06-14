"use client"

import { useEffect, useRef, useState } from "react"
import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import { getChildDeck } from "@/lib/taxonomy/focus-nav"
import { rankBreakdownLabel } from "@/lib/taxonomy/ranks"
import { ChildOverviewCard } from "./ChildOverviewCard"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { cn } from "@/lib/utils"

export function ChildColumn({
  focus,
  focusTaxid,
  selectedIndex,
  onSelectIndex,
  onDrill,
  isBusy,
  className,
}: {
  focus: TaxonRollup
  focusTaxid: number
  selectedIndex: number
  onSelectIndex: (index: number) => void
  onDrill: (row: TaxonRollup, sourceEl: HTMLButtonElement | null) => void
  isBusy?: boolean
  className?: string
}) {
  const { visible, hidden, hiddenCount } = getChildDeck(focusTaxid)
  const [dustOpen, setDustOpen] = useState(false)
  const listRef = useRef<HTMLDivElement>(null)
  const rankLabel = rankBreakdownLabel(focus)

  useEffect(() => {
    setDustOpen(false)
  }, [focusTaxid])

  useEffect(() => {
    const card = listRef.current?.querySelector(`[data-focus-card][data-selected="true"]`)
    card?.scrollIntoView({ block: "nearest", behavior: "smooth" })
  }, [selectedIndex])

  if (visible.length === 0 && hiddenCount === 0) {
    return (
      <div
        className={cn(
          "flex h-full min-h-[8rem] items-center justify-center rounded-xl border border-dashed border-border/50 p-4 text-center text-sm text-muted-foreground",
          className,
        )}
      >
        No direct children in mock slice
      </div>
    )
  }

  return (
    <section
      className={cn(
        "flex max-h-[calc(100vh-12rem)] min-h-0 flex-col gap-2 overflow-hidden rounded-xl border border-border/50 bg-card/30 p-2",
        className,
      )}
      aria-label="Direct children"
    >
      <div className="shrink-0 space-y-0.5 px-1">
        <h3 className="text-sm font-medium">Children</h3>
        {rankLabel && <p className="text-xs text-muted-foreground">{rankLabel}</p>}
      </div>
      <div ref={listRef} className="child-column-list min-h-0 flex-1 space-y-2 overflow-y-auto overscroll-y-contain pr-1">
        {visible.map((row, i) => (
          <ChildOverviewCard
            key={row.taxid}
            row={row}
            compact
            selected={selectedIndex === i}
            onSelect={() => onSelectIndex(i)}
            onClick={(e) => {
              if (isBusy) return
              onDrill(row, e.currentTarget)
            }}
          />
        ))}
        {hiddenCount > 0 && (
          <button
            type="button"
            disabled={isBusy}
            onClick={() => setDustOpen((o) => !o)}
            className="flex w-full flex-col items-center justify-center rounded-lg border border-dashed border-muted-foreground/40 bg-muted/20 px-2 py-3 text-center hover:bg-muted/40 disabled:opacity-50"
          >
            <span className="text-xs font-medium">Dust</span>
            <span className="font-mono text-sm tabular-nums text-muted-foreground">+{hiddenCount}</span>
          </button>
        )}
      </div>
      {dustOpen && hidden.length > 0 && (
        <div className="max-h-40 shrink-0 overflow-auto rounded-lg border border-border">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Name</TableHead>
                <TableHead className="text-right">Mx</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {hidden.map((row) => (
                <TableRow
                  key={row.taxid}
                  className="cursor-pointer hover:bg-secondary/50"
                  onClick={() => {
                    if (isBusy) return
                    onDrill(row, null)
                  }}
                >
                  <TableCell className="max-w-[8rem] truncate text-xs">{row.scientific_name}</TableCell>
                  <TableCell className="text-right font-mono text-xs">
                    {row.species_count_matrix.toLocaleString()}
                  </TableCell>
                </TableRow>
              ))}
            </TableBody>
          </Table>
        </div>
      )}
    </section>
  )
}

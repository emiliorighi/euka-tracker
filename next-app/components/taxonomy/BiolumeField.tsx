"use client"

import { useMemo, useState } from "react"
import { hierarchy, pack } from "d3-hierarchy"
import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import type { TaxonomyLens } from "@/lib/taxonomy-mock/types"
import { lensStyle } from "@/lib/taxonomy/lensEncoding"
import { cladeIsGhost } from "./GhostCladeHint"
import { TaxonomySvg } from "./TaxonomySvg"
import { cn } from "@/lib/utils"

type PackNode = {
  taxid: number
  row: TaxonRollup
  children?: PackNode[]
}

export function BiolumeField({
  focus,
  cells,
  lens = "catalog",
  selectedTaxid,
  onSelect,
  className,
}: {
  focus: TaxonRollup
  cells: TaxonRollup[]
  lens?: TaxonomyLens
  selectedTaxid?: number | null
  onSelect?: (row: TaxonRollup) => void
  className?: string
}) {
  const [hovered, setHovered] = useState<number | null>(null)
  const [internalSelected, setInternalSelected] = useState<number | null>(null)
  const selected = selectedTaxid ?? internalSelected

  const layout = useMemo(() => {
    const root = hierarchy<PackNode>({
      taxid: focus.taxid,
      row: focus,
      children: cells.map((row) => ({ taxid: row.taxid, row })),
    })
      .sum((d) => Math.max(1, Math.log1p(d.row.species_count_ncbi)))
      .sort((a, b) => (b.value ?? 0) - (a.value ?? 0))

    const size = 480
    pack<PackNode>().size([size, size]).padding(4)(root)
    return { nodes: root.leaves(), size }
  }, [focus, cells])

  return (
    <div className={cn("relative mx-auto w-full min-w-0 max-w-xl", className)}>
      <TaxonomySvg baseSize={layout.size} padding={8}>
        {layout.nodes.map((node) => {
          const row = node.data.row
          if (row.taxid === focus.taxid) return null
          const style = lensStyle(row, lens)
          const ghost = cladeIsGhost(row)
          const r = node.r ?? 4
          const dimmed = hovered != null && hovered !== row.taxid
          const isSel = selected === row.taxid
          const cx = node.x ?? 0
          const cy = node.y ?? 0
          const annotRate =
            row.species_count_matrix > 0
              ? row.species_with_annotation / row.species_count_matrix
              : 0
          return (
            <g
              key={row.taxid}
              className="cursor-pointer transition-opacity duration-200"
              style={{ opacity: dimmed ? 0.35 : 1 }}
              onMouseEnter={() => setHovered(row.taxid)}
              onMouseLeave={() => setHovered(null)}
              onClick={() => {
                setInternalSelected(row.taxid)
                onSelect?.(row)
              }}
            >
              <circle
                cx={cx}
                cy={cy}
                r={r}
                fill={ghost ? "var(--ghost-clade)" : style.fill}
                fillOpacity={style.opacity}
                stroke={isSel ? "var(--primary)" : style.stroke ?? "var(--ghost-border)"}
                strokeWidth={isSel ? 2 : row.species_threatened > 0 ? 1.5 : 1}
                className={cn("lens-crossfade", style.pulse && "biolume-pulse")}
              />
              {row.species_threatened > 0 && r > 8 && (
                <circle cx={cx} cy={cy} r={Math.max(2, r * 0.2)} fill="var(--risk-amber)" opacity={0.85} />
              )}
              {annotRate > 0.3 && r > 8 && (
                <circle
                  cx={cx + r * 0.35}
                  cy={cy - r * 0.35}
                  r={Math.max(1.5, r * 0.12)}
                  fill="var(--annotation-teal)"
                  opacity={0.9}
                />
              )}
              {r > 22 && (
                <text
                  x={cx}
                  y={cy}
                  textAnchor="middle"
                  dominantBaseline="middle"
                  className="fill-foreground pointer-events-none text-[9px]"
                >
                  {row.scientific_name.split(" ")[0]?.slice(0, 10)}
                </text>
              )}
            </g>
          )
        })}
      </TaxonomySvg>
    </div>
  )
}

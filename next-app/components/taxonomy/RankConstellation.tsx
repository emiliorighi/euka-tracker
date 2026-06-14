"use client"

import { useMemo, useState } from "react"
import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import type { TaxonomyLens } from "@/lib/taxonomy-mock/types"
import { formatDualCount } from "@/lib/taxonomy-mock"
import { lensStyle } from "@/lib/taxonomy/lensEncoding"
import { CladeTooltipCard } from "./CladeTooltip"
import { TaxonomySvg } from "./TaxonomySvg"
import { cn } from "@/lib/utils"

const GOLDEN = Math.PI * (3 - Math.sqrt(5))

export function RankConstellation({
  focus,
  stars,
  lens = "catalog",
  selectedTaxid,
  onSelect,
  className,
}: {
  focus: TaxonRollup
  stars: TaxonRollup[]
  lens?: TaxonomyLens
  selectedTaxid?: number | null
  onSelect?: (row: TaxonRollup) => void
  className?: string
}) {
  const [hovered, setHovered] = useState<number | null>(null)
  const size = 520
  const cx = size / 2
  const cy = size / 2
  const maxNcbi = Math.max(...stars.map((s) => s.species_count_ncbi), 1)

  const positions = useMemo(() => {
    return stars.map((star, i) => {
      const angle = i * GOLDEN * 2 - Math.PI / 2
      const t = Math.sqrt(star.species_count_ncbi / maxNcbi)
      const dist = 50 + t * 160
      return {
        star,
        x: cx + dist * Math.cos(angle),
        y: cy + dist * Math.sin(angle),
        r: 4 + t * 12,
      }
    })
  }, [stars, cx, cy, maxNcbi])

  const hoveredStar = hovered != null ? stars.find((s) => s.taxid === hovered) : null

  return (
    <div className={cn("relative mx-auto w-full min-w-0 max-w-xl", className)}>
      {hoveredStar && (
        <div className="pointer-events-none absolute left-2 top-2 z-10 hidden sm:block">
          <CladeTooltipCard row={hoveredStar} />
        </div>
      )}
      <TaxonomySvg baseSize={size} padding={52}>
        {Array.from({ length: 40 }).map((_, i) => (
          <circle
            key={i}
            cx={(i * 47) % size}
            cy={(i * 83) % size}
            r={1}
            fill="var(--foreground)"
            opacity={0.04}
          />
        ))}
        <circle cx={cx} cy={cy} r={28} fill="var(--biolume-dim)" stroke="var(--primary)" strokeWidth={1} />
        <text x={cx} y={cy + 4} textAnchor="middle" className="fill-foreground text-[10px] font-medium">
          {focus.scientific_name}
        </text>
        {positions.map(({ star, x, y, r }) => {
          const style = lensStyle(star, lens)
          const selected = selectedTaxid === star.taxid
          return (
            <g
              key={star.taxid}
              className="cursor-pointer"
              onMouseEnter={() => setHovered(star.taxid)}
              onMouseLeave={() => setHovered(null)}
              onClick={() => onSelect?.(star)}
            >
              <title>{`${star.scientific_name} — ${formatDualCount(star.species_count_matrix, star.species_count_ncbi)}`}</title>
              <line x1={cx} y1={cy} x2={x} y2={y} stroke="var(--ghost-border)" strokeWidth={0.5} opacity={0.4} />
              <circle
                cx={x}
                cy={y}
                r={r}
                fill={style.fill}
                fillOpacity={style.opacity}
                stroke={selected ? "var(--primary)" : style.stroke}
                strokeWidth={selected ? 2 : 1}
                className={cn("lens-crossfade", style.pulse && "biolume-pulse")}
              />
              <text x={x} y={y + r + 8} textAnchor="middle" className="fill-muted-foreground text-[6px]">
                {star.scientific_name.length > 12
                  ? star.scientific_name.slice(0, 10) + "…"
                  : star.scientific_name}
              </text>
            </g>
          )
        })}
      </TaxonomySvg>
    </div>
  )
}

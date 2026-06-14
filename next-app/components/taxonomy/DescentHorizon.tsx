"use client"

import { useMemo } from "react"
import type { CSSProperties } from "react"
import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import { formatDualCount } from "@/lib/taxonomy-mock"
import { cladeIsGhost, ringFillOpacity } from "./GhostCladeHint"
import { TaxonomySvg } from "./TaxonomySvg"
import { cn } from "@/lib/utils"

function ringRadii(ncbi: number, maxNcbi: number, inner: number, outer: number) {
  const t = maxNcbi > 0 ? Math.sqrt(ncbi / maxNcbi) : 0
  const r = inner + t * (outer - inner)
  return { rOuter: r, rInner: r * 0.55 }
}

function describeArc(
  cx: number,
  cy: number,
  rOuter: number,
  rInner: number,
  startAngle: number,
  endAngle: number,
) {
  const large = endAngle - startAngle > Math.PI ? 1 : 0
  const x1 = cx + rOuter * Math.cos(startAngle)
  const y1 = cy + rOuter * Math.sin(startAngle)
  const x2 = cx + rOuter * Math.cos(endAngle)
  const y2 = cy + rOuter * Math.sin(endAngle)
  const x3 = cx + rInner * Math.cos(endAngle)
  const y3 = cy + rInner * Math.sin(endAngle)
  const x4 = cx + rInner * Math.cos(startAngle)
  const y4 = cy + rInner * Math.sin(startAngle)
  return [
    `M ${x1} ${y1}`,
    `A ${rOuter} ${rOuter} 0 ${large} 1 ${x2} ${y2}`,
    `L ${x3} ${y3}`,
    `A ${rInner} ${rInner} 0 ${large} 0 ${x4} ${y4}`,
    "Z",
  ].join(" ")
}

export function DescentHorizon({
  focus,
  children,
  selectedTaxid,
  focusKey,
  onSelect,
  className,
}: {
  focus: TaxonRollup
  children: TaxonRollup[]
  selectedTaxid?: number
  focusKey?: number
  onSelect: (row: TaxonRollup) => void
  className?: string
}) {
  const size = 520
  const cx = size / 2
  const cy = size / 2
  const maxNcbi = Math.max(focus.species_count_ncbi, ...children.map((c) => c.species_count_ncbi), 1)

  const parentRing = ringRadii(focus.species_count_ncbi, maxNcbi, 40, 90)
  const childMaxR = 180

  const sectors = useMemo(() => {
    const n = children.length || 1
    return children.map((child, i) => {
      const start = (i / n) * Math.PI * 2 - Math.PI / 2
      const end = ((i + 1) / n) * Math.PI * 2 - Math.PI / 2
      const { rOuter, rInner } = ringRadii(child.species_count_ncbi, maxNcbi, 90, childMaxR)
      return { child, start, end, rOuter, rInner, path: describeArc(cx, cy, rOuter, rInner, start, end) }
    })
  }, [children, cx, cy, maxNcbi])

  const focusFill = ringFillOpacity(focus)
  const focusGhost = cladeIsGhost(focus)

  return (
    <TaxonomySvg
      baseSize={size}
      padding={56}
      className={className}
      role="listbox"
      aria-label={`Children of ${focus.scientific_name}`}
    >
      <g key={focusKey ?? focus.taxid}>
        <circle
          cx={cx}
          cy={cy}
          r={parentRing.rOuter}
          fill={focusGhost ? "var(--ghost-clade)" : "var(--biolume-dim)"}
          stroke="var(--ghost-border)"
          strokeWidth={1}
          opacity={0.9}
        />
        <circle
          cx={cx}
          cy={cy}
          r={parentRing.rInner}
          fill="var(--primary)"
          className="lens-crossfade"
          opacity={focusFill}
        />
        <text x={cx} y={cy - 4} textAnchor="middle" className="fill-foreground text-[11px] font-medium">
          {focus.scientific_name.length > 22 ? focus.scientific_name.slice(0, 20) + "…" : focus.scientific_name}
        </text>
        <text x={cx} y={cy + 12} textAnchor="middle" className="fill-muted-foreground text-[9px]">
          {focus.species_count_matrix.toLocaleString()} / {focus.species_count_ncbi.toLocaleString()}
        </text>

        {sectors.map(({ child, path, rOuter }, i) => {
          const ghost = cladeIsGhost(child)
          const fill = ringFillOpacity(child)
          const selected = selectedTaxid === child.taxid
          const mid = (i + 0.5) / children.length
          const angle = mid * Math.PI * 2 - Math.PI / 2
          const lx = cx + (rOuter + 8) * Math.cos(angle)
          const ly = cy + (rOuter + 8) * Math.sin(angle)
          const tip = `${child.scientific_name} — ${formatDualCount(child.species_count_matrix, child.species_count_ncbi)}`
          return (
            <g
              key={child.taxid}
              role="option"
              aria-selected={selected}
              className="descent-enter cursor-pointer transition-opacity hover:opacity-100"
              style={{ "--stagger-index": i, opacity: selected ? 1 : 0.88 } as CSSProperties}
              onClick={() => onSelect(child)}
            >
              <title>{tip}</title>
              <path
                d={path}
                fill={ghost ? "var(--ghost-clade)" : "var(--primary)"}
                fillOpacity={ghost ? 0.5 : fill}
                stroke={selected ? "var(--primary)" : "var(--ghost-border)"}
                strokeWidth={selected ? 2 : 1}
                className="lens-crossfade"
              />
              <text
                x={lx}
                y={ly}
                textAnchor="middle"
                className="fill-foreground pointer-events-none text-[7px]"
              >
                {child.scientific_name.length > 14
                  ? child.scientific_name.slice(0, 12) + "…"
                  : child.scientific_name}
              </text>
            </g>
          )
        })}
      </g>
    </TaxonomySvg>
  )
}

export function MiniHorizonRing({
  row,
  size = 120,
  className,
}: {
  row: TaxonRollup
  size?: number
  className?: string
}) {
  const cx = size / 2
  const cy = size / 2
  const r = size * 0.4
  const ri = r * 0.55
  const ghost = cladeIsGhost(row)
  const fill = ringFillOpacity(row)
  return (
    <svg viewBox={`0 0 ${size} ${size}`} className={className} width={size} height={size}>
      <circle
        cx={cx}
        cy={cy}
        r={r}
        fill={ghost ? "var(--ghost-clade)" : "var(--biolume-dim)"}
        stroke="var(--ghost-border)"
      />
      <circle cx={cx} cy={cy} r={ri} fill="var(--primary)" opacity={fill} />
      <text x={cx} y={cy + 4} textAnchor="middle" className="fill-foreground text-[8px]">
        {row.scientific_name.split(" ")[0]?.slice(0, 12)}
      </text>
    </svg>
  )
}

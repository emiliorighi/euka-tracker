import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import { formatNumber, pctCatalogLabel } from "@/lib/taxonomy-mock"
import { MiniHorizonRing } from "./DescentHorizon"
import { DualCountBadge } from "./DualCountBadge"
import { FunnelDiffRow } from "./FunnelCathedral"
import { TaxonName } from "./TaxonName"
import { cn } from "@/lib/utils"

const RANK_COLS: { total: keyof TaxonRollup; data: keyof TaxonRollup; label: string }[] = [
  { total: "order_nodes_total", data: "order_nodes_with_data", label: "Orders" },
  { total: "family_nodes_total", data: "family_nodes_with_data", label: "Families" },
  { total: "genus_nodes_total", data: "genus_nodes_with_data", label: "Genera" },
]

function threatenedPct(row: TaxonRollup): number {
  if (row.species_iucn_assessed <= 0) return 0
  return row.species_threatened / row.species_iucn_assessed
}

export function SymbiosisCompare({
  left,
  right,
  sharedAncestor,
  className,
}: {
  left: TaxonRollup
  right: TaxonRollup
  sharedAncestor?: TaxonRollup
  className?: string
}) {
  return (
    <div className={cn("min-w-0 space-y-8", className)}>
      {sharedAncestor && (
        <p className="text-center text-sm text-muted-foreground">
          Shared ancestor:{" "}
          <span className="text-primary">{sharedAncestor.scientific_name}</span>
        </p>
      )}
      <div className="grid min-w-0 gap-8 md:grid-cols-2">
        <ComparePanel row={left} side="left" />
        <ComparePanel row={right} side="right" />
      </div>
      <div className="mx-auto min-w-0 max-w-md space-y-3 rounded-xl border border-border bg-card/50 p-4">
        <h3 className="text-xs font-medium uppercase tracking-widest text-muted-foreground">
          Funnel diff
        </h3>
        <FunnelDiffRow
          label="Catalog species"
          left={left.species_count_matrix}
          right={right.species_count_matrix}
        />
        <FunnelDiffRow
          label="With assembly"
          left={left.species_with_assembly}
          right={right.species_with_assembly}
        />
        <FunnelDiffRow
          label="With annotation"
          left={left.species_with_annotation}
          right={right.species_with_annotation}
        />
        <FunnelDiffRow
          label="Threatened (count)"
          left={left.species_threatened}
          right={right.species_threatened}
        />
        <FunnelDiffRow
          label="Threatened (% assessed)"
          left={Math.round(threatenedPct(left) * 100)}
          right={Math.round(threatenedPct(right) * 100)}
        />
      </div>
      <RankCompareTable left={left} right={right} />
    </div>
  )
}

function ComparePanel({ row, side }: { row: TaxonRollup; side: "left" | "right" }) {
  return (
    <div className="flex min-w-0 flex-col items-center gap-4 rounded-xl border border-border bg-card/30 p-4">
      <TaxonName name={row.scientific_name} className="text-lg" />
      <span className="text-xs capitalize text-muted-foreground">{row.rank}</span>
      <MiniHorizonRing row={row} size={140} />
      <DualCountBadge matrix={row.species_count_matrix} ncbi={row.species_count_ncbi} />
      <p className="text-xs text-muted-foreground">{pctCatalogLabel(row)} catalog coverage</p>
      <span className="sr-only">{side} panel</span>
    </div>
  )
}

function RankCompareTable({ left, right }: { left: TaxonRollup; right: TaxonRollup }) {
  return (
    <div className="min-w-0 overflow-x-auto rounded-xl border border-border">
      <table className="w-full min-w-[280px] text-sm">
        <thead>
          <tr className="border-b border-border bg-secondary/40 text-left text-xs text-muted-foreground">
            <th className="px-4 py-2">Rank level</th>
            <th className="px-4 py-2">{left.scientific_name}</th>
            <th className="px-4 py-2">{right.scientific_name}</th>
          </tr>
        </thead>
        <tbody>
          {RANK_COLS.map(({ total, data, label }) => {
            const lt = left[total] as number
            const ld = left[data] as number
            const rt = right[total] as number
            const rd = right[data] as number
            if (lt === 0 && rt === 0) return null
            return (
              <tr key={label} className="border-b border-border/60">
                <td className="px-4 py-2 text-muted-foreground">{label}</td>
                <td className="px-4 py-2 font-mono tabular-nums">
                  {formatNumber(ld)} / {formatNumber(lt)}
                </td>
                <td className="px-4 py-2 font-mono tabular-nums">
                  {formatNumber(rd)} / {formatNumber(rt)}
                </td>
              </tr>
            )
          })}
        </tbody>
      </table>
    </div>
  )
}

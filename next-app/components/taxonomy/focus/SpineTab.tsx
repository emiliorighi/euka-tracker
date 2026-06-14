"use client"

import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import { formatDualCount, pctCatalog } from "@/lib/taxonomy-mock"
import { TaxonName } from "../TaxonName"
import { cn } from "@/lib/utils"

export function SpineTab({
  row,
  variant = "ancestor",
  onClick,
  className,
  tabRef,
  disabled,
}: {
  row: TaxonRollup
  variant?: "ancestor" | "parent"
  onClick?: (e: React.MouseEvent<HTMLButtonElement>) => void
  className?: string
  tabRef?: React.Ref<HTMLButtonElement>
  disabled?: boolean
}) {
  const lit = pctCatalog(row)
  const hue = 160 + row.depth_from_eukaryota * 2
  const label = row.scientific_name.split(" ")[0] ?? row.scientific_name

  return (
    <button
      ref={tabRef}
      type="button"
      onClick={onClick}
      disabled={disabled || !onClick}
      title={`${row.scientific_name} — ${formatDualCount(row.species_count_matrix, row.species_count_ncbi)}`}
      aria-label={
        variant === "parent"
          ? `Go up to ${row.scientific_name}`
          : `Jump to ${row.scientific_name}`
      }
      className={cn(
        "spine-tab flex min-h-[4rem] w-full items-center justify-center rounded-lg border px-1 py-3 disabled:opacity-50",
        variant === "parent"
          ? "border-primary/35 bg-primary/10 hover:bg-primary/15"
          : "border-border/60 bg-card/40 hover:bg-secondary/80",
        onClick && !disabled && "cursor-pointer",
        className,
      )}
      style={{
        backgroundColor: `oklch(0.16 0.012 ${hue} / ${0.35 + lit * 0.45})`,
      }}
    >
      <span
        className={cn(
          "max-h-[7rem] truncate text-[10px] font-medium leading-tight tracking-wide",
          variant === "parent" ? "text-primary" : "text-muted-foreground",
        )}
        style={{ writingMode: "vertical-rl", textOrientation: "mixed" }}
      >
        <TaxonName name={label} />
      </span>
    </button>
  )
}

import { formatDualCount } from "@/lib/taxonomy-mock"
import { cn } from "@/lib/utils"

export function DualCountBadge({
  matrix,
  ncbi,
  className,
}: {
  matrix: number
  ncbi: number
  className?: string
}) {
  const pct = ncbi > 0 ? ((matrix / ncbi) * 100).toFixed(1) : "0"
  return (
    <span className={cn("inline-flex flex-col gap-0.5", className)}>
      <span className="font-mono text-sm tabular-nums">{formatDualCount(matrix, ncbi)}</span>
      <span className="text-xs text-muted-foreground">{pct}% catalog coverage</span>
    </span>
  )
}

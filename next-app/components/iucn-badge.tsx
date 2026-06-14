import { IUCN_META, type IucnStatus } from "@/lib/biodiversity-data"
import { cn } from "@/lib/utils"

export function IucnBadge({
  status,
  className,
  showLabel = false,
}: {
  status: IucnStatus
  className?: string
  showLabel?: boolean
}) {
  const meta = IUCN_META[status]
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border border-border/60 bg-secondary/60 px-2 py-0.5 text-xs font-medium",
        className,
      )}
      title={meta.label}
    >
      <span
        className="size-2 rounded-full"
        style={{ backgroundColor: meta.color }}
        aria-hidden
      />
      <span className="font-mono">{meta.short}</span>
      {showLabel && <span className="text-muted-foreground">{meta.label}</span>}
    </span>
  )
}

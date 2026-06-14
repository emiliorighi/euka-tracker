import { Card } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { LucideIcon } from "lucide-react"

export function AtlasStatCard({
  icon: Icon,
  label,
  value,
  unit,
  sublabel,
  accent = false,
  className,
}: {
  icon: LucideIcon
  label: string
  value: string | number
  unit?: string
  sublabel?: string
  accent?: boolean
  className?: string
}) {
  return (
    <Card className={cn("gap-0 border-border/60 bg-card/50 p-4", className)}>
      <div className="flex items-center justify-between">
        <span className="text-xs text-muted-foreground">{label}</span>
        <span
          className={cn(
            "flex size-7 items-center justify-center rounded-md",
            accent ? "bg-primary/15 text-primary" : "bg-secondary/80 text-muted-foreground",
          )}
        >
          <Icon className="size-3.5" />
        </span>
      </div>
      <div className="mt-2 flex items-baseline gap-1">
        <span className="text-2xl font-semibold tracking-tight tabular-nums">{value}</span>
        {unit && <span className="text-xs text-muted-foreground">{unit}</span>}
      </div>
      {sublabel && <p className="mt-0.5 text-[10px] text-muted-foreground">{sublabel}</p>}
    </Card>
  )
}

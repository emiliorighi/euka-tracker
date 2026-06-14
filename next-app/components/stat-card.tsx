import { Card } from "@/components/ui/card"
import { cn } from "@/lib/utils"
import type { LucideIcon } from "lucide-react"

export function StatCard({
  icon: Icon,
  label,
  value,
  unit,
  sublabel,
  accent = false,
}: {
  icon: LucideIcon
  label: string
  value: string | number
  unit?: string
  sublabel?: string
  accent?: boolean
}) {
  return (
    <Card className="gap-0 p-5">
      <div className="flex items-center justify-between">
        <span className="text-sm text-muted-foreground">{label}</span>
        <span
          className={cn(
            "flex size-8 items-center justify-center rounded-lg",
            accent ? "bg-primary/15 text-primary" : "bg-secondary text-muted-foreground",
          )}
        >
          <Icon className="size-4" />
        </span>
      </div>
      <div className="mt-3 flex items-baseline gap-1.5">
        <span className="text-3xl font-semibold tracking-tight tabular-nums">{value}</span>
        {unit && <span className="text-sm text-muted-foreground">{unit}</span>}
      </div>
      {sublabel && <p className="mt-1 text-xs text-muted-foreground">{sublabel}</p>}
    </Card>
  )
}

import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

export function LitTreeStage({ children, className }: { children: ReactNode; className?: string }) {
  return (
    <div className={cn("lit-tree-stage flex min-h-0 min-w-0 flex-1 flex-col", className)}>
      {children}
    </div>
  )
}

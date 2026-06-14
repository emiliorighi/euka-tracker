import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

export function ConceptStage({
  viz,
  panel,
  rail,
  footer,
  depthHue,
  className,
}: {
  viz: ReactNode
  panel?: ReactNode
  rail?: ReactNode
  footer?: ReactNode
  depthHue?: number
  className?: string
}) {
  const bgStyle = depthHue != null
    ? { backgroundColor: `oklch(0.16 0.012 ${depthHue})` }
    : undefined

  return (
    <div className={cn("flex min-h-0 min-w-0 flex-1 flex-col gap-4", className)}>
      <div
        className={cn(
          "grid min-h-0 min-w-0 flex-1 gap-4",
          rail
            ? panel
              ? "lg:grid-cols-[180px_minmax(0,1fr)_260px]"
              : "lg:grid-cols-[180px_minmax(0,1fr)]"
            : panel
              ? "lg:grid-cols-[minmax(0,1fr)_260px]"
              : "grid-cols-1",
        )}
      >
        {rail && (
          <aside className="hidden min-w-0 overflow-y-auto lg:block lg:max-h-[70vh]">
            {rail}
          </aside>
        )}
        <div
          className="flex min-h-[280px] min-w-0 items-center justify-center overflow-auto rounded-xl border border-border/50 p-3 md:min-h-[320px] md:p-4"
          style={bgStyle}
        >
          {viz}
        </div>
        {panel && (
          <aside className="min-w-0 overflow-y-auto lg:sticky lg:top-4 lg:max-h-[70vh] lg:self-start">
            {panel}
          </aside>
        )}
      </div>
      {rail && <div className="overflow-x-auto lg:hidden">{rail}</div>}
      {footer && <div className="min-w-0 shrink-0">{footer}</div>}
    </div>
  )
}

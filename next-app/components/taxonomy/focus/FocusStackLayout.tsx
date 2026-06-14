import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

export function FocusStackLayout({
  left,
  center,
  right,
  mobileNav,
  isBusy,
  className,
}: {
  left: ReactNode
  center: ReactNode
  right: ReactNode
  mobileNav?: ReactNode
  isBusy?: boolean
  className?: string
}) {
  return (
    <div
      className={cn("flex min-h-0 min-w-0 flex-1 flex-col gap-3", isBusy && "pointer-events-none", className)}
      aria-busy={isBusy || undefined}
    >
      {mobileNav}
      <div
        className={cn(
          "grid min-h-0 min-w-0 flex-1 gap-3 md:gap-4",
          "grid-cols-1 md:grid-cols-[3rem_minmax(0,1fr)_11rem] lg:grid-cols-[3.5rem_minmax(0,1fr)_13rem]",
        )}
      >
        <aside className="hidden min-h-0 min-w-0 flex-col md:flex">{left}</aside>
        <main className="min-h-0 min-w-0 overflow-hidden">{center}</main>
        <aside className="hidden min-h-0 min-w-0 md:block">{right}</aside>
      </div>
      <div className="min-h-0 min-w-0 md:hidden">{right}</div>
    </div>
  )
}

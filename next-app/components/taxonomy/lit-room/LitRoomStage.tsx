import type { ReactNode } from "react"
import { cn } from "@/lib/utils"

export function LitRoomStage({
  filament,
  chamber,
  mobileNav,
  isBusy,
  className,
}: {
  filament: ReactNode
  chamber: ReactNode
  mobileNav?: ReactNode
  isBusy?: boolean
  className?: string
}) {
  return (
    <div
      className={cn(
        "lit-room-stage flex min-h-0 min-w-0 flex-1 flex-col gap-3",
        isBusy && "pointer-events-none",
        className,
      )}
      aria-busy={isBusy || undefined}
    >
      <div
        className={cn(
          "grid min-h-0 min-w-0 flex-1 gap-3 md:gap-4",
          "grid-cols-1 md:grid-cols-[4rem_minmax(0,1fr)]",
        )}
      >
        {mobileNav && <div className="col-span-full min-w-0 md:hidden">{mobileNav}</div>}
        <aside className="hidden min-h-0 min-w-0 md:col-start-1 md:row-start-1 md:flex">{filament}</aside>
        <main className="min-h-0 min-w-0 overflow-hidden md:col-start-2 md:row-start-1">{chamber}</main>
      </div>
    </div>
  )
}

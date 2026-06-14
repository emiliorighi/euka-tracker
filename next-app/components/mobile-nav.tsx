"use client"

import Link from "next/link"
import { usePathname } from "next/navigation"
import {
  LayoutDashboard,
  Map as MapIcon,
  Network,
  Leaf,
  Dna,
  ScatterChart,
  Sparkles,
} from "lucide-react"
import { cn } from "@/lib/utils"

const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard },
  { href: "/taxonomy/atlas?view=scatter", label: "Atlas", icon: ScatterChart },
  { href: "/map", label: "Map", icon: MapIcon },
  { href: "/taxonomy", label: "Taxonomy", icon: Network },
  { href: "/taxonomy/concepts", label: "Concepts", icon: Sparkles },
  { href: "/species", label: "Species", icon: Leaf },
]

export function MobileNav() {
  const pathname = usePathname()
  return (
    <div className="md:hidden">
      <header className="flex h-14 items-center gap-2.5 border-b border-border bg-sidebar px-4">
        <div className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <Dna className="size-4" />
        </div>
        <span className="text-sm font-semibold">EukaryoBase</span>
      </header>
      <nav className="sticky top-0 z-30 flex items-center gap-1 overflow-x-auto border-b border-border bg-sidebar/95 px-2 py-2 backdrop-blur">
        {NAV.map((item) => {
          const active =
            item.href === "/taxonomy"
              ? pathname === "/taxonomy"
              : pathname === item.href ||
                (item.href !== "/" && pathname.startsWith(item.href + "/"))
          const Icon = item.icon
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex shrink-0 items-center gap-2 rounded-lg px-3 py-2 text-sm font-medium transition-colors",
                active ? "bg-sidebar-accent text-foreground" : "text-muted-foreground",
              )}
            >
              <Icon className={cn("size-4", active && "text-primary")} />
              {item.label}
            </Link>
          )
        })}
      </nav>
    </div>
  )
}

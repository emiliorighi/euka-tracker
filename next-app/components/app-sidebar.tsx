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
  PanelLeftClose,
  PanelLeft,
  Sparkles,
  Layers,
  DoorOpen,
  TreePine,
} from "lucide-react"
import { useState } from "react"
import { cn } from "@/lib/utils"

const NAV = [
  { href: "/", label: "Dashboard", icon: LayoutDashboard, desc: "Overview" },
  { href: "/taxonomy/atlas", label: "Atlas", icon: ScatterChart, desc: "Tree + scatter" },
  { href: "/map", label: "Geographic Map", icon: MapIcon, desc: "Sampling sites" },
  { href: "/taxonomy", label: "Taxonomy Explorer", icon: Network, desc: "Clade metrics" },
  { href: "/taxonomy/concepts", label: "Taxonomy Concepts", icon: Sparkles, desc: "UX prototypes" },
  { href: "/taxonomy/focus", label: "Taxonomy Focus", icon: Layers, desc: "Focus stack drill" },
  { href: "/taxonomy/lit-room", label: "Taxonomy Lit Room", icon: DoorOpen, desc: "Lit chamber drill" },
  { href: "/taxonomy/atlas", label: "Taxonomy Atlas", icon: TreePine, desc: "Tree + dashboard" },
  { href: "/species", label: "Species Catalogue", icon: Leaf, desc: "All records" },
]

export function AppSidebar() {
  const pathname = usePathname()
  const [collapsed, setCollapsed] = useState(false)

  return (
    <aside
      className={cn(
        "sticky top-0 hidden h-screen shrink-0 flex-col border-r border-sidebar-border bg-sidebar md:flex",
        "transition-[width] duration-300 ease-out",
        collapsed ? "w-[76px]" : "w-64",
      )}
    >
      <div className="flex h-16 items-center gap-2.5 border-b border-sidebar-border px-4">
        <div className="flex size-9 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground">
          <Dna className="size-5" />
        </div>
        {!collapsed && (
          <div className="min-w-0">
            <p className="truncate text-sm font-semibold tracking-tight">EukaryoBase</p>
            <p className="truncate text-xs text-muted-foreground">Genomics Atlas</p>
          </div>
        )}
      </div>

      <nav className="flex flex-1 flex-col gap-1 p-3">
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
              title={collapsed ? item.label : undefined}
              className={cn(
                "group flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors",
                active
                  ? "bg-sidebar-accent text-foreground"
                  : "text-muted-foreground hover:bg-sidebar-accent/60 hover:text-foreground",
              )}
            >
              <Icon
                className={cn(
                  "size-5 shrink-0 transition-colors",
                  active ? "text-primary" : "text-muted-foreground group-hover:text-foreground",
                )}
              />
              {!collapsed && (
                <span className="flex min-w-0 flex-col">
                  <span className="truncate font-medium leading-tight">{item.label}</span>
                  <span className="truncate text-xs text-muted-foreground">{item.desc}</span>
                </span>
              )}
              {active && !collapsed && (
                <span className="ml-auto size-1.5 rounded-full bg-primary" aria-hidden />
              )}
            </Link>
          )
        })}
      </nav>

      <div className="border-t border-sidebar-border p-3">
        <button
          type="button"
          onClick={() => setCollapsed((c) => !c)}
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-muted-foreground transition-colors hover:bg-sidebar-accent/60 hover:text-foreground"
        >
          {collapsed ? (
            <PanelLeft className="size-5 shrink-0" />
          ) : (
            <>
              <PanelLeftClose className="size-5 shrink-0" />
              <span>Collapse</span>
            </>
          )}
        </button>
      </div>
    </aside>
  )
}

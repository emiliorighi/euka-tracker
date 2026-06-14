"use client"

import Link from "next/link"
import type { ReactNode } from "react"
import type { TaxonomyLens } from "@/lib/taxonomy-mock/types"
import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import { formatDualCount } from "@/lib/taxonomy-mock"
import { LENS_LABELS } from "@/lib/taxonomy/lensEncoding"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import { ArrowLeft } from "lucide-react"

const LENSES: TaxonomyLens[] = ["catalog", "genome", "risk", "reads"]

const CONCEPT_LINKS = [
  { href: "/taxonomy/focus", label: "Focus" },
  { href: "/taxonomy/concepts/descent", label: "Descent" },
  { href: "/taxonomy/concepts/biolume", label: "Biolume" },
  { href: "/taxonomy/concepts/constellation", label: "Constellation" },
  { href: "/taxonomy/concepts/funnel", label: "Funnel" },
  { href: "/taxonomy/concepts/specimen-stream", label: "Stream" },
  { href: "/taxonomy/concepts/symbiosis", label: "Symbiosis" },
] as const

export function ConceptShell({
  title,
  description,
  backHref = "/taxonomy/concepts",
  focusRow,
  currentPath,
  lens,
  onLensChange,
  headerExtra,
  children,
}: {
  title: string
  description: string
  backHref?: string
  focusRow?: TaxonRollup
  currentPath?: string
  lens?: TaxonomyLens
  onLensChange?: (l: TaxonomyLens) => void
  headerExtra?: ReactNode
  children: ReactNode
}) {
  return (
    <div className="flex min-h-0 min-w-0 flex-1 flex-col gap-4">
      <header className="min-w-0 shrink-0 border-b border-border pb-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="min-w-0 space-y-2">
            <Button variant="ghost" size="sm" asChild className="-ml-2 h-8 px-2">
              <Link href={backHref}>
                <ArrowLeft className="mr-1 size-4" />
                Concepts
              </Link>
            </Button>
            <div>
              <h1 className="text-xl font-semibold tracking-tight">{title}</h1>
              <p className="max-w-2xl text-sm text-muted-foreground">{description}</p>
              {focusRow && (
                <p className="mt-1 font-mono text-xs text-primary">
                  {formatDualCount(focusRow.species_count_matrix, focusRow.species_count_ncbi)}
                </p>
              )}
            </div>
            <nav className="flex flex-wrap gap-x-2 gap-y-1 text-xs text-muted-foreground" aria-label="Concept demos">
              {CONCEPT_LINKS.map((c) => (
                <Link
                  key={c.href}
                  href={c.href}
                  className={cn(
                    "hover:text-foreground",
                    currentPath === c.href && "font-medium text-primary",
                  )}
                >
                  {c.label}
                </Link>
              ))}
            </nav>
          </div>
          <div className="flex flex-wrap items-center gap-2">
            {headerExtra}
            {lens && onLensChange && (
              <div className="flex max-w-full flex-wrap rounded-lg border border-border bg-card p-0.5">
                {LENSES.map((l) => (
                  <button
                    key={l}
                    type="button"
                    title={LENS_LABELS[l]}
                    onClick={() => onLensChange(l)}
                    className={cn(
                      "rounded-md px-2.5 py-1 text-xs transition-colors",
                      lens === l
                        ? "bg-primary text-primary-foreground"
                        : "text-muted-foreground hover:text-foreground",
                    )}
                  >
                    {LENS_LABELS[l].split(" ")[0]}
                  </button>
                ))}
              </div>
            )}
          </div>
        </div>
      </header>
      <div className="min-h-0 min-w-0 flex-1">{children}</div>
    </div>
  )
}

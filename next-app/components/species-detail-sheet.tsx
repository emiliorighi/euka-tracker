"use client"

import { Boxes, Dna, ExternalLink } from "lucide-react"
import { IucnBadge } from "@/components/iucn-badge"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { iucnMetaForCategory } from "@/lib/iucn/config"
import { type IucnSpeciesDatum, truthyFlag } from "@/lib/iucn/types"

function FlagRow({ label, active }: { label: string; active: boolean }) {
  return (
    <div className="flex items-center justify-between rounded-md border border-border/60 bg-secondary/30 px-2.5 py-1.5 text-xs">
      <span className="text-muted-foreground">{label}</span>
      <span className={active ? "font-medium text-foreground" : "text-muted-foreground/60"}>
        {active ? "Yes" : "—"}
      </span>
    </div>
  )
}

type Props = {
  species: IucnSpeciesDatum | null
  open: boolean
  onOpenChange: (open: boolean) => void
}

export function SpeciesDetailSheet({
  species,
  open,
  onOpenChange,
}: Props) {
  const meta = species ? iucnMetaForCategory(species.redlistCategory) : null

  return (
    <Sheet open={open} onOpenChange={onOpenChange} modal={false}>
      <SheetContent side="right" modal={false} inset className="w-full gap-0 overflow-y-auto sm:max-w-md">
        {species && (
          <>
            <SheetHeader className="border-b border-border">
              <div className="flex items-center gap-2">
                <IucnBadge category={species.redlistCategory} showLabel />
              </div>
              <SheetTitle className="text-xl italic">
                {species.scientificName?.trim() || "Unknown species"}
              </SheetTitle>
              <SheetDescription>
                {species.speciesName?.trim() && species.speciesName !== species.scientificName
                  ? species.speciesName
                  : species.redlistCategory?.trim() || "IUCN Red List assessment"}
              </SheetDescription>
            </SheetHeader>

            <div className="space-y-6 p-4">
              <section>
                <h3 className="mb-2 text-xs font-medium uppercase tracking-widest text-muted-foreground">
                  Taxonomy
                </h3>
                <div className="flex flex-wrap items-center gap-1.5 text-sm">
                  {[
                    species.kingdomName,
                    species.phylumName,
                    species.className,
                    species.orderName,
                    species.familyName,
                    species.genusName,
                  ]
                    .filter(Boolean)
                    .map((t, i) => (
                      <span key={`${i}-${t}`} className="flex items-center gap-1.5">
                        {i > 0 && <span className="text-muted-foreground/50">/</span>}
                        <span className="rounded-md bg-secondary px-2 py-0.5 text-xs">{t}</span>
                      </span>
                    ))}
                </div>
              </section>

              {species.populationTrend ? (
                <section className="flex items-center justify-between rounded-lg border border-border bg-secondary/40 p-3 text-sm">
                  <span className="text-muted-foreground">Population trend</span>
                  <span className="font-medium">{species.populationTrend}</span>
                </section>
              ) : null}

              <section>
                <h3 className="mb-3 text-xs font-medium uppercase tracking-widest text-muted-foreground">
                  Data availability
                </h3>
                <div className="grid grid-cols-2 gap-2">
                  <FlagRow label="GBIF" active={truthyFlag(species.hasGbif)} />
                  <FlagRow label="iNaturalist" active={truthyFlag(species.hasInat)} />
                  <FlagRow label="GOAT" active={truthyFlag(species.hasGoat)} />
                  <FlagRow label="Assemblies" active={truthyFlag(species.hasAssemblies)} />
                  <FlagRow label="Annotations" active={truthyFlag(species.hasAnnotations)} />
                  <FlagRow label="Short WGS" active={truthyFlag(species.hasShortWgs)} />
                  <FlagRow label="Long WGS" active={truthyFlag(species.hasLongWgs)} />
                  <FlagRow label="Short RNA-seq" active={truthyFlag(species.hasShortTranscriptomic)} />
                  <FlagRow label="Long RNA-seq" active={truthyFlag(species.hasLongTranscriptomic)} />
                </div>
              </section>

              <section>
                <h3 className="mb-2 text-xs font-medium uppercase tracking-widest text-muted-foreground">
                  External IDs
                </h3>
                <div className="space-y-2 text-sm">
                  {species.ncbiTaxid ? (
                    <IdLink
                      label="NCBI TaxID"
                      href={`https://www.ncbi.nlm.nih.gov/Taxonomy/Browser/wwwtax.cgi?id=${species.ncbiTaxid}`}
                      value={String(species.ncbiTaxid)}
                    />
                  ) : null}
                  {species.gbifId ? (
                    <IdLink
                      label="GBIF"
                      href={`https://www.gbif.org/species/${species.gbifId}`}
                      value={String(species.gbifId)}
                    />
                  ) : null}
                  {species.inatId ? (
                    <IdLink
                      label="iNaturalist"
                      href={`https://www.inaturalist.org/taxa/${species.inatId}`}
                      value={String(species.inatId)}
                    />
                  ) : null}
                  {!species.ncbiTaxid && !species.gbifId && !species.inatId ? (
                    <p className="text-xs text-muted-foreground">No linked external IDs</p>
                  ) : null}
                </div>
              </section>

              {meta ? (
                <p
                  className="rounded-lg border p-3 text-xs leading-relaxed"
                  style={{
                    borderColor: `color-mix(in oklch, ${meta.color} 40%, transparent)`,
                    backgroundColor: `color-mix(in oklch, ${meta.color} 10%, transparent)`,
                  }}
                >
                  Conservation status:{" "}
                  <span className="font-medium">{meta.label}</span>
                  {species.assessmentId ? (
                    <>
                      {" "}
                      · Assessment{" "}
                      <span className="font-mono">{species.assessmentId}</span>
                    </>
                  ) : null}
                </p>
              ) : null}

              <section className="flex items-center gap-2 text-xs text-muted-foreground">
                <Dna className="size-3.5" />
                <Boxes className="size-3.5" />
                <span>Genomic flags from IUCN species matrix</span>
              </section>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}

function IdLink({
  label,
  href,
  value,
}: {
  label: string
  href: string
  value: string
}) {
  return (
    <a
      href={href}
      target="_blank"
      rel="noopener noreferrer"
      className="flex items-center justify-between rounded-md border border-border/60 px-2.5 py-1.5 hover:bg-secondary/50"
    >
      <span className="text-muted-foreground">{label}</span>
      <span className="flex items-center gap-1 font-mono text-xs">
        {value}
        <ExternalLink className="size-3" />
      </span>
    </a>
  )
}

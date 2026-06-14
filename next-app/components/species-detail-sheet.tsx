"use client"

import {
  type Species,
  formatGenomeSize,
  IUCN_META,
} from "@/lib/biodiversity-data"
import { IucnBadge } from "@/components/iucn-badge"
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet"
import { MapPin, Dna, Boxes, Gauge, Calendar, FlaskConical } from "lucide-react"

export function SpeciesDetailSheet({
  species,
  open,
  onOpenChange,
}: {
  species: Species | null
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full gap-0 overflow-y-auto sm:max-w-md">
        {species && (
          <>
            <SheetHeader className="border-b border-border">
              <div className="flex items-center gap-2">
                <IucnBadge status={species.iucn} showLabel />
              </div>
              <SheetTitle className="text-xl italic">{species.scientificName}</SheetTitle>
              <SheetDescription>{species.commonName}</SheetDescription>
            </SheetHeader>

            <div className="space-y-6 p-4">
              {/* Taxonomy lineage */}
              <section>
                <h3 className="mb-2 text-xs font-medium uppercase tracking-widest text-muted-foreground">
                  Taxonomy
                </h3>
                <div className="flex flex-wrap items-center gap-1.5 text-sm">
                  {[
                    species.kingdom,
                    species.phylum,
                    species.class,
                    species.order,
                    species.family,
                  ].map((t, i) => (
                    <span key={`${i}-${t}`} className="flex items-center gap-1.5">
                      {i > 0 && <span className="text-muted-foreground/50">/</span>}
                      <span className="rounded-md bg-secondary px-2 py-0.5 text-xs">{t}</span>
                    </span>
                  ))}
                </div>
              </section>

              {/* Location */}
              <section>
                <h3 className="mb-2 text-xs font-medium uppercase tracking-widest text-muted-foreground">
                  Locality
                </h3>
                <div className="flex items-center gap-2 text-sm">
                  <MapPin className="size-4 text-primary" />
                  <span className="font-medium">{species.country}</span>
                  <span className="font-mono text-xs text-muted-foreground">
                    {species.lat.toFixed(2)}, {species.lng.toFixed(2)}
                  </span>
                </div>
              </section>

              {/* Genomics */}
              <section>
                <h3 className="mb-3 text-xs font-medium uppercase tracking-widest text-muted-foreground">
                  Genome assembly
                </h3>
                <div className="grid grid-cols-2 gap-3">
                  <DetailStat icon={Dna} label="Genome size" value={formatGenomeSize(species.genomeSizeMb)} />
                  <DetailStat icon={Gauge} label="GC content" value={`${species.gcContent}%`} />
                  <DetailStat icon={Boxes} label="Chromosomes" value={String(species.chromosomes)} />
                  <DetailStat icon={Gauge} label="BUSCO" value={`${species.busco}%`} />
                  <DetailStat icon={Boxes} label="Scaffold N50" value={`${species.scaffoldN50Mb} Mb`} />
                  <DetailStat icon={FlaskConical} label="Samples" value={String(species.sampleCount)} />
                </div>
              </section>

              <section className="flex items-center justify-between rounded-lg border border-border bg-secondary/40 p-3 text-sm">
                <span className="flex items-center gap-2 text-muted-foreground">
                  <Boxes className="size-4" /> Assembly level
                </span>
                <span className="font-medium">{species.assemblyLevel}</span>
              </section>

              <section className="flex items-center justify-between rounded-lg border border-border bg-secondary/40 p-3 text-sm">
                <span className="flex items-center gap-2 text-muted-foreground">
                  <Calendar className="size-4" /> First sequenced
                </span>
                <span className="font-medium">{species.sequencedYear}</span>
              </section>

              <p
                className="rounded-lg border p-3 text-xs leading-relaxed"
                style={{
                  borderColor: `color-mix(in oklch, ${IUCN_META[species.iucn].color} 40%, transparent)`,
                  backgroundColor: `color-mix(in oklch, ${IUCN_META[species.iucn].color} 10%, transparent)`,
                }}
              >
                Conservation status:{" "}
                <span className="font-medium">{IUCN_META[species.iucn].label}</span>. Genomic
                resources support population monitoring and ex-situ conservation planning.
              </p>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}

function DetailStat({
  icon: Icon,
  label,
  value,
}: {
  icon: typeof MapPin
  label: string
  value: string
}) {
  return (
    <div className="rounded-lg border border-border bg-secondary/40 p-3">
      <div className="flex items-center gap-1.5 text-xs text-muted-foreground">
        <Icon className="size-3.5" />
        {label}
      </div>
      <p className="mt-1 text-sm font-semibold tabular-nums">{value}</p>
    </div>
  )
}

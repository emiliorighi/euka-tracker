"use client"

import { useState, useMemo } from "react"
import { PageHeader } from "@/components/page-header"
import { SpeciesDetailSheet } from "@/components/species-detail-sheet"
import { IucnBadge } from "@/components/iucn-badge"
import {
  SPECIES,
  type Species,
  type IucnStatus,
  IUCN_META,
  IUCN_ORDER,
  formatGenomeSize,
  formatNumber,
} from "@/lib/biodiversity-data"
import { Input } from "@/components/ui/input"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { Card } from "@/components/ui/card"
import { Search, ArrowUpDown } from "lucide-react"

type SortKey = "scientificName" | "genomeSizeMb" | "busco" | "sampleCount"

const KINGDOMS = ["All", "Animalia", "Plantae", "Fungi"]

export default function SpeciesPage() {
  const [query, setQuery] = useState("")
  const [kingdom, setKingdom] = useState("All")
  const [status, setStatus] = useState<string>("All")
  const [sortKey, setSortKey] = useState<SortKey>("scientificName")
  const [sortAsc, setSortAsc] = useState(true)
  const [selected, setSelected] = useState<Species | null>(null)
  const [open, setOpen] = useState(false)

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase()
    const list = SPECIES.filter((s) => {
      const matchesQuery =
        !q ||
        s.scientificName.toLowerCase().includes(q) ||
        s.commonName.toLowerCase().includes(q) ||
        s.family.toLowerCase().includes(q)
      const matchesKingdom = kingdom === "All" || s.kingdom === kingdom
      const matchesStatus = status === "All" || s.iucn === status
      return matchesQuery && matchesKingdom && matchesStatus
    })
    list.sort((a, b) => {
      const av = a[sortKey]
      const bv = b[sortKey]
      const cmp = typeof av === "string" ? av.localeCompare(bv as string) : (av as number) - (bv as number)
      return sortAsc ? cmp : -cmp
    })
    return list
  }, [query, kingdom, status, sortKey, sortAsc])

  function toggleSort(key: SortKey) {
    if (sortKey === key) setSortAsc((v) => !v)
    else {
      setSortKey(key)
      setSortAsc(true)
    }
  }

  function openSpecies(s: Species) {
    setSelected(s)
    setOpen(true)
  }

  return (
    <div className="flex flex-col gap-6">
      <PageHeader
        title="Species Catalogue"
        description="Browse all sequenced Eukaryote species. Search, filter, and sort, then select any row for full genomic metadata."
      />

      {/* Filters */}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-center">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            placeholder="Search by name or family..."
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            className="pl-9"
          />
        </div>
        <Select value={kingdom} onValueChange={setKingdom}>
          <SelectTrigger className="sm:w-44">
            <SelectValue placeholder="Kingdom" />
          </SelectTrigger>
          <SelectContent>
            {KINGDOMS.map((k) => (
              <SelectItem key={k} value={k}>
                {k === "All" ? "All kingdoms" : k}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
        <Select value={status} onValueChange={setStatus}>
          <SelectTrigger className="sm:w-52">
            <SelectValue placeholder="IUCN status" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="All">All IUCN statuses</SelectItem>
            {IUCN_ORDER.map((s) => (
              <SelectItem key={s} value={s}>
                {IUCN_META[s].label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      <p className="text-sm text-muted-foreground">
        Showing <span className="font-medium text-foreground">{formatNumber(filtered.length)}</span>{" "}
        of {formatNumber(SPECIES.length)} species
      </p>

      <Card className="overflow-hidden border-border bg-card p-0">
        <div className="overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="hover:bg-transparent">
                <SortHead label="Species" active={sortKey === "scientificName"} asc={sortAsc} onClick={() => toggleSort("scientificName")} />
                <TableHead>Taxonomy</TableHead>
                <TableHead>IUCN</TableHead>
                <SortHead label="Genome" active={sortKey === "genomeSizeMb"} asc={sortAsc} onClick={() => toggleSort("genomeSizeMb")} numeric />
                <SortHead label="BUSCO" active={sortKey === "busco"} asc={sortAsc} onClick={() => toggleSort("busco")} numeric />
                <SortHead label="Samples" active={sortKey === "sampleCount"} asc={sortAsc} onClick={() => toggleSort("sampleCount")} numeric />
              </TableRow>
            </TableHeader>
            <TableBody>
              {filtered.map((s) => (
                <TableRow
                  key={s.id}
                  onClick={() => openSpecies(s)}
                  className="cursor-pointer"
                >
                  <TableCell>
                    <div className="font-medium italic">{s.scientificName}</div>
                    <div className="text-xs text-muted-foreground">{s.commonName}</div>
                  </TableCell>
                  <TableCell>
                    <div className="text-sm">{s.class}</div>
                    <div className="text-xs text-muted-foreground">{s.family}</div>
                  </TableCell>
                  <TableCell>
                    <IucnBadge status={s.iucn} />
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm tabular-nums">
                    {formatGenomeSize(s.genomeSizeMb)}
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm tabular-nums">
                    {s.busco.toFixed(1)}%
                  </TableCell>
                  <TableCell className="text-right font-mono text-sm tabular-nums">
                    {formatNumber(s.sampleCount)}
                  </TableCell>
                </TableRow>
              ))}
              {filtered.length === 0 && (
                <TableRow>
                  <TableCell colSpan={6} className="h-32 text-center text-muted-foreground">
                    No species match your filters.
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </div>
      </Card>

      <SpeciesDetailSheet species={selected} open={open} onOpenChange={setOpen} />
    </div>
  )
}

function SortHead({
  label,
  active,
  asc,
  onClick,
  numeric,
}: {
  label: string
  active: boolean
  asc: boolean
  onClick: () => void
  numeric?: boolean
}) {
  return (
    <TableHead className={numeric ? "text-right" : undefined}>
      <button
        onClick={onClick}
        className={`inline-flex items-center gap-1 transition-colors hover:text-foreground ${
          active ? "text-foreground" : ""
        } ${numeric ? "flex-row-reverse" : ""}`}
      >
        {label}
        <ArrowUpDown className={`size-3 ${active ? "opacity-100" : "opacity-40"} ${active && !asc ? "rotate-180" : ""} transition-transform`} />
      </button>
    </TableHead>
  )
}

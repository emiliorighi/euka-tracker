import Link from "next/link"
import { Dna } from "lucide-react"
import { AtlasTaxonomyProvider } from "@/lib/atlas-taxonomy/AtlasTaxonomyProvider"

export default function TaxonomyAtlasLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <div className="fixed inset-0 z-50 flex flex-col bg-background">
      <header className="flex h-12 shrink-0 items-center justify-between border-b border-border/60 px-4 md:px-6">
        <div className="flex items-center gap-2.5">
          <div className="flex size-8 items-center justify-center rounded-lg bg-primary text-primary-foreground">
            <Dna className="size-4" />
          </div>
          <div className="min-w-0">
            <p className="text-sm font-semibold tracking-tight">EukaryoBase Atlas</p>
            <p className="hidden text-[10px] text-muted-foreground sm:block">
              Taxonomy explorer · rank-colored tree
            </p>
          </div>
        </div>
        <Link
          href="/taxonomy/concepts"
          className="inline-flex h-8 items-center rounded-md border border-border px-3 text-xs text-muted-foreground transition-colors hover:bg-secondary/60 hover:text-foreground"
        >
          Exit to Concepts
        </Link>
      </header>
      <div className="min-h-0 flex-1 overflow-hidden">
        <AtlasTaxonomyProvider>{children}</AtlasTaxonomyProvider>
      </div>
    </div>
  )
}

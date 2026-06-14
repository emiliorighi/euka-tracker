import { cn } from "@/lib/utils"

export function TaxonName({
  name,
  className,
}: {
  name: string
  className?: string
}) {
  return <em className={cn("font-medium italic text-foreground", className)}>{name}</em>
}

import type { ReactNode, SVGProps } from "react"
import { cn } from "@/lib/utils"

export function TaxonomySvg({
  baseSize = 520,
  padding = 48,
  className,
  children,
  ...props
}: {
  baseSize?: number
  padding?: number
  className?: string
  children: ReactNode
} & Omit<SVGProps<SVGSVGElement>, "viewBox">) {
  const dim = baseSize + padding * 2
  const viewBox = `${-padding} ${-padding} ${dim} ${dim}`

  return (
    <svg
      viewBox={viewBox}
      preserveAspectRatio="xMidYMid meet"
      className={cn(
        "mx-auto h-auto w-full max-h-[min(70vh,32rem)] max-w-full",
        className,
      )}
      {...props}
    >
      {children}
    </svg>
  )
}

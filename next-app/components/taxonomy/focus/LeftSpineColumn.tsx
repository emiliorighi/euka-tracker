"use client"

import type { TaxonRollup } from "@/lib/taxonomy-mock/types"
import { AncestorSpine } from "./AncestorSpine"
import { ParentBookmark } from "./ParentBookmark"
import { cn } from "@/lib/utils"

export function LeftSpineColumn({
  focusTaxid,
  onJump,
  onAscend,
  parentTabRef,
  disabled,
  className,
}: {
  focusTaxid: number
  onJump: (taxid: number) => void
  onAscend: (parent: TaxonRollup, el: HTMLButtonElement) => void
  parentTabRef?: React.Ref<HTMLButtonElement>
  disabled?: boolean
  className?: string
}) {
  return (
    <div className={cn("flex h-full min-h-0 flex-col gap-2", className)}>
      <div className="min-h-0 flex-1 overflow-y-auto">
        <AncestorSpine focusTaxid={focusTaxid} onJump={onJump} disabled={disabled} />
      </div>
      <div className="mt-auto shrink-0">
        <ParentBookmark
          focusTaxid={focusTaxid}
          onAscend={onAscend}
          tabRef={parentTabRef}
          disabled={disabled}
        />
      </div>
    </div>
  )
}

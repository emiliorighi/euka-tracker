"use client"

import * as React from "react"
import { cn } from "@/lib/utils"

type CollapsibleContextValue = {
  open: boolean
  onOpenChange: (open: boolean) => void
}

const CollapsibleContext = React.createContext<CollapsibleContextValue | null>(null)

function useCollapsible() {
  const ctx = React.useContext(CollapsibleContext)
  if (!ctx) throw new Error("Collapsible components must be used within Collapsible")
  return ctx
}

function Collapsible({
  open: openProp,
  defaultOpen,
  onOpenChange,
  className,
  children,
  ...props
}: React.ComponentProps<"div"> & {
  open?: boolean
  defaultOpen?: boolean
  onOpenChange?: (open: boolean) => void
}) {
  const [uncontrolledOpen, setUncontrolledOpen] = React.useState(defaultOpen ?? false)
  const open = openProp ?? uncontrolledOpen
  const setOpen = React.useCallback(
    (next: boolean) => {
      onOpenChange?.(next)
      if (openProp === undefined) setUncontrolledOpen(next)
    },
    [onOpenChange, openProp],
  )

  return (
    <CollapsibleContext.Provider value={{ open, onOpenChange: setOpen }}>
      <div data-slot="collapsible" className={cn(className)} {...props}>
        {children}
      </div>
    </CollapsibleContext.Provider>
  )
}

function CollapsibleTrigger({
  className,
  children,
  ...props
}: React.ComponentProps<"button">) {
  const { open, onOpenChange } = useCollapsible()
  return (
    <button
      type="button"
      data-slot="collapsible-trigger"
      aria-expanded={open}
      className={cn("w-full text-left", className)}
      onClick={() => onOpenChange(!open)}
      {...props}
    >
      {children}
    </button>
  )
}

function CollapsibleContent({
  className,
  children,
  ...props
}: React.ComponentProps<"div">) {
  const { open } = useCollapsible()
  if (!open) return null
  return (
    <div data-slot="collapsible-content" className={cn(className)} {...props}>
      {children}
    </div>
  )
}

export { Collapsible, CollapsibleTrigger, CollapsibleContent }

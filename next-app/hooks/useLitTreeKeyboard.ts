"use client"

import { useEffect } from "react"

export function useLitTreeKeyboard(handlers: {
  onEscape?: () => void
  onArrowUp?: () => void
  onArrowDown?: () => void
  onEnter?: () => void
  enabled?: boolean
}) {
  const { onEscape, onArrowUp, onArrowDown, onEnter, enabled = true } = handlers

  useEffect(() => {
    if (!enabled) return

    const onKey = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName
      if (tag === "INPUT" || tag === "SELECT" || tag === "TEXTAREA") return

      switch (e.key) {
        case "Escape":
          onEscape?.()
          break
        case "ArrowUp":
          e.preventDefault()
          onArrowUp?.()
          break
        case "ArrowDown":
          e.preventDefault()
          onArrowDown?.()
          break
        case "Enter":
          onEnter?.()
          break
      }
    }

    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [enabled, onEscape, onArrowUp, onArrowDown, onEnter])
}

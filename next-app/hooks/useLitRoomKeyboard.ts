"use client"

import { useEffect } from "react"

export function useLitRoomKeyboard(handlers: {
  onEscape?: () => void
  onArrowUp?: () => void
  onArrowDown?: () => void
  onArrowLeft?: () => void
  onArrowRight?: () => void
  onEnter?: () => void
  enabled?: boolean
}) {
  const {
    onEscape,
    onArrowUp,
    onArrowDown,
    onArrowLeft,
    onArrowRight,
    onEnter,
    enabled = true,
  } = handlers

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
        case "ArrowLeft":
          e.preventDefault()
          onArrowLeft?.()
          break
        case "ArrowRight":
          e.preventDefault()
          onArrowRight?.()
          break
        case "Enter":
          onEnter?.()
          break
      }
    }

    window.addEventListener("keydown", onKey)
    return () => window.removeEventListener("keydown", onKey)
  }, [enabled, onEscape, onArrowUp, onArrowDown, onArrowLeft, onArrowRight, onEnter])
}

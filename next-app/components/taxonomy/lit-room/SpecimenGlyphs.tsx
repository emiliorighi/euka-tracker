import type { SpecimenSpeciesRow } from "@/lib/taxonomy-mock/types"
import { stoneTierFlags } from "./lit-room-utils"

export function SpecimenGlyphs({ row }: { row: SpecimenSpeciesRow }) {
  const { reads, asm, annot } = stoneTierFlags(row)
  return (
    <div className="specimen-glyphs flex gap-1" aria-label="Data tiers">
      <GlyphDot active={reads} label="Reads" hue={195} />
      <GlyphDot active={asm} label="Assembly" hue={152} />
      <GlyphDot active={annot} label="Annotation" hue={245} />
    </div>
  )
}

function GlyphDot({ active, label, hue }: { active: boolean; label: string; hue: number }) {
  return (
    <span
      className="specimen-glyph size-1.5 rounded-full transition-all duration-300"
      style={{
        background: active ? `oklch(0.7 0.14 ${hue})` : "oklch(1 0 0 / 12%)",
        boxShadow: active ? `0 0 6px oklch(0.7 0.14 ${hue} / 0.8)` : undefined,
      }}
      title={label}
    />
  )
}

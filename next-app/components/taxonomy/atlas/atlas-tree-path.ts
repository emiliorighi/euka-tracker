import { getAtlasAncestorsOf } from "@/lib/atlas-taxonomy"
import type { TaxonRollup } from "@/lib/taxonomy-mock/types"

export function getSelectionPath(selectedTaxid: number): TaxonRollup[] {
  return getAtlasAncestorsOf(selectedTaxid)
}

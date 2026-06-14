/** Layout tokens for the atlas hierarchy tree (up to ~35 ranks from Eukaryota). */
export const ATLAS_TREE_MAX_DEPTH = 35
export const ATLAS_TREE_INDENT_REM = 0.75
export const ATLAS_TREE_GUTTER_REM = 1.5
/** Fixed row stride: py-1 wrapper + py-1.5 card + text-xs line (~2.5rem at 16px root). */
export const ATLAS_TREE_ROW_HEIGHT_REM = 2.5
/** Left grid column: room for deep indents + horizontal scroll. */
export const ATLAS_TREE_COLUMN_MIN = "34rem"
export const ATLAS_TREE_COLUMN_MAX = "52vw"
/** Content width when fully expanded to max depth (scroll target, not always applied). */
export const ATLAS_TREE_MIN_WIDTH_REM =
  ATLAS_TREE_MAX_DEPTH * ATLAS_TREE_INDENT_REM + ATLAS_TREE_GUTTER_REM + 11

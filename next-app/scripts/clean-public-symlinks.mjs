#!/usr/bin/env node
/** Remove broken public/ symlinks before static export (GitHub Pages). */
import { existsSync, lstatSync, readlinkSync, unlinkSync } from "node:fs"
import { dirname, resolve } from "node:path"
import { fileURLToPath } from "node:url"

const here = dirname(fileURLToPath(import.meta.url))
const publicDir = resolve(here, "../public")

for (const name of ["staged", "tiles", "data"]) {
  const linkPath = resolve(publicDir, name)
  if (!existsSync(linkPath)) continue
  const stat = lstatSync(linkPath)
  if (!stat.isSymbolicLink()) continue
  const target = resolve(publicDir, readlinkSync(linkPath))
  if (!existsSync(target)) {
    unlinkSync(linkPath)
    console.log(`Removed broken symlink public/${name}`)
  }
}

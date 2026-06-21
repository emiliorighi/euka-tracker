#!/usr/bin/env node
/** Symlink site-data into public/ for local dev (tiles + rollups/manifest). */
import { existsSync, lstatSync, mkdirSync, readlinkSync, rmSync, symlinkSync } from "node:fs"
import { dirname, relative, resolve } from "node:path"
import { fileURLToPath } from "node:url"

const here = dirname(fileURLToPath(import.meta.url))
const appRoot = resolve(here, "..")
const publicDir = resolve(appRoot, "public")
const siteDataRoot = resolve(appRoot, "../site-data")

const links = [
  { name: "tiles", target: resolve(siteDataRoot, "tiles") },
  { name: "data", target: resolve(siteDataRoot, "data") },
]

mkdirSync(publicDir, { recursive: true })

for (const { name, target } of links) {
  const linkPath = resolve(publicDir, name)
  if (!existsSync(target)) {
    console.warn(`Skip public/${name}: ${target} does not exist`)
    continue
  }

  if (existsSync(linkPath)) {
    const stat = lstatSync(linkPath)
    if (stat.isSymbolicLink()) {
      const current = resolve(publicDir, readlinkSync(linkPath))
      if (current === target) {
        console.log(`public/${name} already linked`)
        continue
      }
    }
    rmSync(linkPath, { recursive: true, force: true })
  }

  const relTarget = relative(publicDir, target)
  symlinkSync(relTarget, linkPath)
  console.log(`Linked public/${name} -> ${relTarget}`)
}

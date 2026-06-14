#!/usr/bin/env node
/** Symlink repo tiles/ into next-app/public/tiles for local dev (port 3000). */
import { existsSync, lstatSync, mkdirSync, rmSync, symlinkSync, unlinkSync } from "node:fs"
import { dirname, relative, resolve } from "node:path"
import { fileURLToPath } from "node:url"

const here = dirname(fileURLToPath(import.meta.url))
const appRoot = resolve(here, "..")
const publicTiles = resolve(appRoot, "public/tiles")
const repoTiles = resolve(appRoot, "..", "tiles")

if (!existsSync(repoTiles)) {
  console.error(`Tiles directory not found: ${repoTiles}`)
  console.error(
    "Run: pipenv run python pipeline/build_scatter_tiles.py --embedding landscape --step all",
  )
  process.exit(1)
}

mkdirSync(resolve(appRoot, "public"), { recursive: true })

if (existsSync(publicTiles)) {
  const stat = lstatSync(publicTiles)
  if (stat.isSymbolicLink()) {
    unlinkSync(publicTiles)
  } else if (stat.isDirectory()) {
    rmSync(publicTiles, { recursive: true, force: true })
  } else {
    rmSync(publicTiles, { force: true })
  }
}

const target = relative(dirname(publicTiles), repoTiles)
symlinkSync(target, publicTiles)
console.log(`Linked public/tiles → ${target}`)

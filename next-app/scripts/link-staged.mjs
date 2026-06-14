#!/usr/bin/env node
/** Symlink repo data/staged into next-app/public/staged for local dev (port 3000). */
import { existsSync, lstatSync, mkdirSync, rmSync, symlinkSync, unlinkSync } from "node:fs"
import { dirname, relative, resolve } from "node:path"
import { fileURLToPath } from "node:url"

const here = dirname(fileURLToPath(import.meta.url))
const appRoot = resolve(here, "..")
const publicStaged = resolve(appRoot, "public/staged")
const repoStaged = resolve(appRoot, "..", "data", "staged")

if (!existsSync(repoStaged)) {
  console.error(`Staged data directory not found: ${repoStaged}`)
  process.exit(1)
}

mkdirSync(resolve(appRoot, "public"), { recursive: true })

if (existsSync(publicStaged)) {
  const stat = lstatSync(publicStaged)
  if (stat.isSymbolicLink()) {
    unlinkSync(publicStaged)
  } else if (stat.isDirectory()) {
    rmSync(publicStaged, { recursive: true, force: true })
  } else {
    rmSync(publicStaged, { force: true })
  }
}

const target = relative(dirname(publicStaged), repoStaged)
symlinkSync(target, publicStaged)
console.log(`Linked public/staged → ${target}`)

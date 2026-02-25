#!/usr/bin/env node
/**
 * Static server that serves the app and returns empty PBF for missing tiles.
 * Run: node server.js
 */
const http = require("http");
const fs = require("fs");
const path = require("path");

const PORT = 3000;
const ROOT = path.join(__dirname);

const REWRITES = {
  "/": "/frontend/index.html",
  "/main.js": "/frontend/main.js",
  "/style.css": "/frontend/style.css",
};
const MIME = {
  ".html": "text/html",
  ".js": "application/javascript",
  ".css": "text/css",
  ".json": "application/json",
  ".pbf": "application/x-protobuf",
};

const server = http.createServer((req, res) => {
  const pathname = (req.url || "").split("?")[0];
  let filePath = REWRITES[pathname] || pathname;
  filePath = path.join(ROOT, filePath);

  // For missing .pbf tiles, return 204 (MapLibre skips gracefully)
  if (pathname.match(/^\/tiles\/\d+\/\d+\/\d+\.pbf$/)) {
    const tilePath = path.join(ROOT, pathname);
    if (!fs.existsSync(tilePath)) {
      res.writeHead(204);
      return res.end();
    }
    filePath = tilePath;
  }

  fs.readFile(filePath, (err, data) => {
    if (err) {
      res.writeHead(404);
      return res.end("Not Found");
    }
    const ext = path.extname(filePath);
    res.writeHead(200, {
      "Content-Type": MIME[ext] || "application/octet-stream",
    });
    res.end(data);
  });
});

server.listen(PORT, () => {
  console.log(`Serving at http://localhost:${PORT}`);
});

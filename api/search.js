/**
 * Search API - returns suggestions for autocomplete.
 * GET /api/search?q=query&limit=10
 *
 * For static deployment: serve search_index.json and use client-side search.
 * This file can be used with Vercel/Netlify serverless.
 */

// In serverless: load search_index.json at cold start
let index = [];

async function loadIndex() {
  if (index.length) return index;
  const fs = await import("fs");
  const path = await import("path");
  const p = path.join(process.cwd(), "output", "search_index.json");
  try {
    const data = fs.readFileSync(p, "utf8");
    index = JSON.parse(data);
  } catch (e) {
    index = [];
  }
  return index;
}

export async function handler(req) {
  const url = new URL(req.url);
  const q = url.searchParams.get("q") || "";
  const limit = parseInt(url.searchParams.get("limit") || "10", 10);

  await loadIndex();
  const query = q.toLowerCase().trim();
  // Tuple format: [id, sci_name, all, lon, lat, zoom, rank]
  const ID = 0, SCI_NAME = 1, ALL = 2, LON = 3, LAT = 4, ZOOM = 5, RANK = 6;
  const hits = index
    .filter(
      (t) =>
        query.length < 2 ||
        (t[SCI_NAME] && t[SCI_NAME].toLowerCase().includes(query)) ||
        (t[ALL] && t[ALL].toLowerCase().includes(query)) ||
        (t[ID] && String(t[ID]).includes(query))
    )
    .slice(0, limit)
    .map((t) => ({
      id: t[ID],
      sci_name: t[SCI_NAME],
      common_name: "",
      coordinates: [t[LON], t[LAT]],
      zoom: t[ZOOM],
    }));

  return new Response(
    JSON.stringify({ suggestions: hits }),
    { headers: { "Content-Type": "application/json" } }
  );
}

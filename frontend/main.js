const TILE_BASE =
  typeof window !== "undefined"
    ? `${window.location.origin}/tiles`
    : "/tiles";
const SEARCH_INDEX_URL = "/output/search_index.json";
const GLYPHS_URL =
  "https://protomaps.github.io/basemaps-assets/fonts/{fontstack}/{range}.pbf";

const EUKA_FILL = "#6599ff";
const BRANCH_COLOR = "rgba(255, 255, 255, 0.75)";
const NODE_COLOR = "#e84393";
const LABEL_COLOR = "#ffffff";
const RANK_LABEL_COLOR = EUKA_FILL;

const map = new maplibregl.Map({
  container: "map",
  style: {
    version: 8,
    glyphs: GLYPHS_URL,
    sources: {
      tiles: {
        type: "vector",
        tiles: [`${TILE_BASE}/{z}/{x}/{y}.pbf`],
        minzoom: 0,
        maxzoom: 10,
      },
    },
    layers: [
      {
        id: "background",
        type: "background",
        paint: { "background-color": "#050510" },
      },

      // Clade fill – semi-transparent blue (instructions §7)
      {
        id: "clade-fill",
        type: "fill",
        source: "tiles",
        "source-layer": "polygons",
        filter: ["==", ["get", "clade"], true],
        paint: {
          "fill-color": EUKA_FILL,
          "fill-opacity": 0.15,
        },
      },

      // Clade outline
      {
        id: "clade-outline",
        type: "line",
        source: "tiles",
        "source-layer": "polygons",
        filter: ["==", ["get", "clade"], true],
        paint: {
          "line-color": EUKA_FILL,
          "line-opacity": 0.12,
          "line-width": [
            "interpolate", ["linear"], ["zoom"],
            0, 0.8,
            10, 0.3,
          ],
        },
      },

      // Branch lines (dendrogram edges)
      {
        id: "branches",
        type: "line",
        source: "tiles",
        "source-layer": "lines",
        filter: ["==", ["get", "branch"], true],
        paint: {
          "line-color": BRANCH_COLOR,
          "line-width": [
            "interpolate", ["linear"], ["zoom"],
            0, 1.4,
            6, 1.0,
            10, 0.4,
          ],
        },
      },

      // Node dots (internal nodes only)
      {
        id: "node-dots",
        type: "circle",
        source: "tiles",
        "source-layer": "points",
        filter: ["all",
          ["==", ["get", "cladecenter"], false],
          ["==", ["get", "tip"], false],
        ],
        paint: {
          "circle-radius": [
            "interpolate", ["linear"], ["zoom"],
            0, 4,
            6, 3,
            10, 2,
          ],
          "circle-color": NODE_COLOR,
          "circle-opacity": 0.9,
        },
      },

      // Clade labels (on clade centers, large clades first)
      {
        id: "clade-labels",
        type: "symbol",
        source: "tiles",
        "source-layer": "points",
        filter: ["all",
          ["==", ["get", "cladecenter"], true],
          [">=", ["get", "nbdesc"], 50],
        ],
        layout: {
          "text-field": ["get", "sci_name"],
          "text-font": ["Noto Sans Medium"],
          "text-size": [
            "interpolate", ["linear"], ["zoom"],
            0, 14,
            6, 13,
            10, 11,
          ],
          "text-anchor": "center",
          "text-max-width": 8,
          "text-allow-overlap": false,
          "text-optional": true,
          "symbol-sort-key": ["-", 0, ["get", "nbdesc"]],
        },
        paint: {
          "text-color": LABEL_COLOR,
          "text-halo-color": "rgba(5, 5, 16, 0.85)",
          "text-halo-width": 2,
        },
      },

      // Rank labels (on rank lines, §7)
      {
        id: "rank-labels",
        type: "symbol",
        source: "tiles",
        "source-layer": "lines",
        filter: ["all",
          ["==", ["get", "rankname"], true],
          ["!=", ["get", "rank"], "no rank"],
          ["!=", ["get", "rank"], "clade"],
        ],
        layout: {
          "text-field": ["get", "rank"],
          "text-font": ["Noto Sans Italic"],
          "text-size": 9,
          "symbol-placement": "line",
          "text-allow-overlap": false,
          "text-optional": true,
        },
        paint: {
          "text-color": RANK_LABEL_COLOR,
          "text-opacity": 0.25,
          "text-halo-color": "rgba(5, 5, 16, 0.5)",
          "text-halo-width": 1,
        },
      },

      // Node labels (non-tip, non-cladecenter)
      {
        id: "node-labels",
        type: "symbol",
        source: "tiles",
        "source-layer": "points",
        filter: ["all",
          ["==", ["get", "cladecenter"], false],
          ["==", ["get", "tip"], false],
          [">=", ["get", "nbdesc"], 10],
        ],
        layout: {
          "text-field": ["get", "sci_name"],
          "text-font": ["Noto Sans Regular"],
          "text-size": [
            "interpolate", ["linear"], ["zoom"],
            0, 11,
            8, 10,
            10, 9,
          ],
          "text-anchor": "top",
          "text-offset": [0, 0.7],
          "text-max-width": 8,
          "text-allow-overlap": false,
          "text-optional": true,
          "symbol-sort-key": ["-", 0, ["get", "nbdesc"]],
        },
        paint: {
          "text-color": "rgba(220, 230, 255, 0.85)",
          "text-halo-color": "rgba(5, 5, 16, 0.7)",
          "text-halo-width": 1.5,
        },
      },

      // Tip labels (leaves, high zoom only)
      {
        id: "tip-labels",
        type: "symbol",
        source: "tiles",
        "source-layer": "points",
        filter: ["==", ["get", "tip"], true],
        minzoom: 8,
        layout: {
          "text-field": ["get", "sci_name"],
          "text-font": ["Noto Sans Regular"],
          "text-size": 9,
          "text-anchor": "left",
          "text-offset": [0.5, 0],
          "text-max-width": 12,
          "text-allow-overlap": false,
          "text-optional": true,
        },
        paint: {
          "text-color": "rgba(200, 210, 230, 0.65)",
          "text-halo-color": "rgba(5, 5, 16, 0.5)",
          "text-halo-width": 1,
        },
      },
    ],
  },
  center: [-6, -0.34],
  zoom: 5,
  maxZoom: 14,
});

// ── Search ──────────────────────────────────────────────────────────────────

let searchIndex = [];

async function loadSearchIndex() {
  try {
    const r = await fetch(SEARCH_INDEX_URL);
    if (r.ok) searchIndex = await r.json();
  } catch {}
}

const ID = 0, SCI_NAME = 1, ALL = 2, LON = 3, LAT = 4, ZOOM = 5, RANK = 6;

function search(query) {
  if (!query || query.length < 2) return [];
  const q = query.toLowerCase();
  return searchIndex
    .filter(
      (t) =>
        (t[SCI_NAME] && t[SCI_NAME].toLowerCase().includes(q)) ||
        (t[ALL] && t[ALL].toLowerCase().includes(q)) ||
        (t[ID] && String(t[ID]).includes(q))
    )
    .slice(0, 10);
}

const searchEl = document.getElementById("search");
const suggestionsEl = document.getElementById("suggestions");

searchEl.addEventListener("input", () => {
  const q = searchEl.value.trim();
  const hits = search(q);
  if (!hits.length) { suggestionsEl.hidden = true; return; }
  suggestionsEl.innerHTML = hits
    .map(
      (t) =>
        `<li data-id="${t[ID]}" data-lon="${t[LON]}" data-lat="${t[LAT]}" data-zoom="${t[ZOOM]}">
          <span class="sci-name">${esc(t[SCI_NAME] || t[ID])}</span>
          <div class="meta">${esc(t[RANK] || "")} · ${t[ID]}</div>
        </li>`
    )
    .join("");
  suggestionsEl.hidden = false;
});

searchEl.addEventListener("keydown", (e) => {
  const items = suggestionsEl.querySelectorAll("li");
  const cur = suggestionsEl.querySelector('[aria-selected="true"]');
  let idx = cur ? [...items].indexOf(cur) : -1;
  if (e.key === "ArrowDown") { e.preventDefault(); idx = Math.min(idx + 1, items.length - 1); }
  else if (e.key === "ArrowUp") { e.preventDefault(); idx = Math.max(idx - 1, 0); }
  else if (e.key === "Enter" && items[idx]) { e.preventDefault(); items[idx].click(); return; }
  items.forEach((el, i) => el.setAttribute("aria-selected", i === idx));
});

document.addEventListener("click", (e) => {
  if (!suggestionsEl.contains(e.target)) suggestionsEl.hidden = true;
});

suggestionsEl.addEventListener("click", (e) => {
  const li = e.target.closest("li");
  if (!li) return;
  map.flyTo({
    center: [parseFloat(li.dataset.lon), parseFloat(li.dataset.lat)],
    zoom: parseInt(li.dataset.zoom, 10) || 8,
    duration: 800,
  });
  suggestionsEl.hidden = true;
  searchEl.value = li.querySelector(".sci-name").textContent;
});

// ── Click popup ─────────────────────────────────────────────────────────────

map.on("click", (e) => {
  const features = map.queryRenderedFeatures(e.point, {
    layers: ["node-dots", "clade-fill"],
  });
  if (!features.length) return;
  const p = features[0].properties;
  new maplibregl.Popup({ maxWidth: "280px" })
    .setLngLat(e.lngLat)
    .setHTML(
      `<h3>${esc(p.sci_name || p.id)}</h3>
       <div class="rank">${esc(p.rank || "")}</div>
       <div class="meta">${p.nbdesc ? Number(p.nbdesc).toLocaleString() + " descendants" : "leaf"}</div>`
    )
    .addTo(map);
});

map.on("mouseenter", "node-dots", () => (map.getCanvas().style.cursor = "pointer"));
map.on("mouseleave", "node-dots", () => (map.getCanvas().style.cursor = ""));

function esc(s) {
  if (!s) return "";
  const d = document.createElement("div");
  d.textContent = s;
  return d.innerHTML;
}

map.on("load", () => loadSearchIndex());
map.on("error", (e) => console.error("Map error:", e));

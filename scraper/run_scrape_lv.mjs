// Latvian retailer egg-listing scrape runner. Mirrors run_scrape.mjs (Spain) but
// targets Latvian chains and adds a national-anchor cage-free metric.
//
// Coverage: Rimi and Barbora (Maxima) are the two large Latvian online grocers
// with machine-readable catalogues. top!, Lidl, Mego and Elvi have no scrapable
// online egg catalogue (SPA-API / no online store / no shoppable listings) and
// return external_only stubs so the figure shows coverage honestly.
//
// Each SKU is classified by EU production code (0 organic, 1 free-range, 2 barn,
// 3 caged, or unknown) via lib/classify.mjs. Two cage-free shares per retailer:
//   strict  = cage-free / all shell-egg SKUs        (unknowns count as not-cage-free)
//   anchor  = (cage-free + unknown*ANCHOR) / all     (unknowns weighted by the
//             national cage-free share, the Latvian analogue of Spain's 33%)

import { mkdir, writeFile } from "node:fs/promises";

import { classify, isShellEgg, codeLabel, isCageFree } from "./lib/classify.mjs";
import { scrape as scrapeRimi }    from "./lib/retailers/rimi.mjs";
import { scrape as scrapeBarbora } from "./lib/retailers/barbora.mjs";
import { scrape as scrapeTop }     from "./lib/retailers/top_lv.mjs";
import { scrape as scrapeLidl }    from "./lib/retailers/lidl_lv.mjs";
import { scrape as scrapeMego }    from "./lib/retailers/mego.mjs";
import { scrape as scrapeElvi }    from "./lib/retailers/elvi.mjs";

// National cage-free production-capacity share, Latvia 2026: cage-free 2,148,753
// of 4,596,707 laying-hen places = 46.7% ~ 0.47 (Eglitis & Kanepajs 2026). Used
// to weight unlabelled SKUs. It is a production-capacity proxy, not a retail
// volume share. Spain's analogue was 0.33.
const ANCHOR = 0.47;

function defaultTag(d = new Date()) {
  const y = d.getFullYear();
  const q = Math.floor(d.getMonth() / 3) + 1;
  return `${y}-Q${q}-LV`;
}

function csvEscape(v) {
  if (v === null || v === undefined) return "";
  const s = String(v);
  return /[",\n]/.test(s) ? `"${s.replace(/"/g, '""')}"` : s;
}
function toCSV(rows, columns) {
  const head = columns.join(",");
  const body = rows.map(r => columns.map(c => csvEscape(r[c])).join(",")).join("\n");
  return head + "\n" + body + "\n";
}

async function main() {
  const tag = process.argv[2] || defaultTag();
  console.log(`Running Latvian scrape for ${tag}`);

  const runners = [
    ["Rimi",    scrapeRimi],
    ["Barbora", scrapeBarbora],
    ["top!",    scrapeTop],
    ["Lidl",    scrapeLidl],
    ["Mego",    scrapeMego],
    ["Elvi",    scrapeElvi],
  ];

  const all = [];
  for (const [label, fn] of runners) {
    try {
      const rows = await fn();
      console.log(`  ${label}: ${rows.length} rows`);
      all.push(...rows);
    } catch (e) {
      console.log(`  ${label}: FAILED — ${e.message}`);
      all.push({ retailer: label, error: e.message });
    }
  }

  for (const r of all) {
    if (r.error || r.source === "external_only") {
      r.eu_code = null; r.production_label = "n/a"; r.is_shell_egg = null;
      r.cage_free = null; r.classify_source = "n/a";
      continue;
    }
    const c = classify(r);
    r.eu_code = c.code;
    r.classify_source = c.source;
    r.production_label = codeLabel(c.code);
    r.is_shell_egg = isShellEgg(r);
    r.cage_free = c.code === null ? null : isCageFree(c.code);
  }

  await mkdir("data/raw", { recursive: true });
  await mkdir("data/summary", { recursive: true });

  const cols = ["retailer", "source", "name", "price_text", "unit_price", "tipo_produccion",
    "eu_code", "production_label", "classify_source", "is_shell_egg", "cage_free", "note", "error"];
  await writeFile(`data/raw/${tag}_listings.csv`, toCSV(all, cols), "utf8");
  await writeFile(`data/raw/${tag}_listings.json`, JSON.stringify(all, null, 2), "utf8");

  const byRetailer = {};
  for (const r of all) {
    const key = r.retailer || "?";
    if (!byRetailer[key]) byRetailer[key] = {
      retailer: key, total_listings: 0, shell_egg_listings: 0,
      organic: 0, free_range: 0, barn: 0, caged: 0, unknown: 0,
      cage_free_listings: 0,
      cage_free_share_strict_pct: null,   // cage-free / all shell eggs (unknowns = not-cage-free)
      cage_free_share_anchor_pct: null,   // (cage-free + unknown*ANCHOR) / all shell eggs
      note: ""
    };
    const b = byRetailer[key];
    if (r.error || r.source === "external_only") {
      b.note = r.note || r.error || "";
      continue;
    }
    b.total_listings++;
    if (!r.is_shell_egg) continue;
    b.shell_egg_listings++;
    if (r.eu_code === 0) b.organic++;
    else if (r.eu_code === 1) b.free_range++;
    else if (r.eu_code === 2) b.barn++;
    else if (r.eu_code === 3) b.caged++;
    else b.unknown++;
    if (r.cage_free) b.cage_free_listings++;
  }
  for (const b of Object.values(byRetailer)) {
    if (b.shell_egg_listings) {
      b.cage_free_share_strict_pct = Math.round(100 * b.cage_free_listings / b.shell_egg_listings);
      b.cage_free_share_anchor_pct = Math.round(100 * (b.cage_free_listings + b.unknown * ANCHOR) / b.shell_egg_listings);
    }
  }
  const summaryRows = Object.values(byRetailer);
  const sumCols = ["retailer", "total_listings", "shell_egg_listings", "organic", "free_range", "barn", "caged", "unknown", "cage_free_listings", "cage_free_share_strict_pct", "cage_free_share_anchor_pct", "note"];
  await writeFile(`data/summary/${tag}_summary.csv`, toCSV(summaryRows, sumCols), "utf8");
  await writeFile(`data/summary/${tag}_summary.json`, JSON.stringify(summaryRows, null, 2), "utf8");

  console.log(`\nNational cage-free anchor: ${Math.round(ANCHOR * 100)}% (Latvia production capacity, Eglitis & Kanepajs 2026)`);
  console.log("Summary by retailer (chicken shell eggs only):");
  console.table(summaryRows.map(b => ({
    retailer: b.retailer,
    listings: b.shell_egg_listings,
    "0-org": b.organic, "1-free": b.free_range, "2-barn": b.barn, "3-cage": b.caged, "?": b.unknown,
    cf_strict: b.cage_free_share_strict_pct,
    cf_anchor: b.cage_free_share_anchor_pct,
  })));
}

await main();

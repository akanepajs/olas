// Latvian retailer egg-listing scrape runner. Mirrors run_scrape.mjs (Spain) but
// targets Latvian chains, adds a national-anchor cage-free metric, per-egg
// pricing, and a daily time-series history.
//
// Coverage: Rimi and Barbora (Maxima) are the large Latvian online grocers with
// full machine-readable catalogues; Lidl publishes its (small) standard egg
// assortment online too. top!, Mego and Elvi have no comparable online egg
// catalogue and return external_only stubs.
//
// Each SKU is classified by EU production code (0 organic, 1 free-range, 2 barn,
// 3 caged, or unknown) via lib/classify.mjs. Per-retailer outputs:
//   strict cage-free %  = cage-free / all shell-egg SKUs
//   anchor cage-free %  = (cage-free + unknown*ANCHOR) / all shell-egg SKUs
//   median price/egg    = median of (pack price / eggs per pack) over shell eggs
//
// Usage: node run_scrape_lv.mjs [tag] [run-date YYYY-MM-DD]
//   tag      defaults to <year>-Q<quarter>-LV (drives the current-snapshot files)
//   run-date defaults to today (the dated row appended to the history series)

import { mkdir, writeFile, readFile } from "node:fs/promises";

import { classify, isShellEgg, codeLabel, isCageFree } from "./lib/classify.mjs";
import { scrape as scrapeRimi }    from "./lib/retailers/rimi.mjs";
import { scrape as scrapeBarbora } from "./lib/retailers/barbora.mjs";
import { scrape as scrapeTop }     from "./lib/retailers/top_lv.mjs";
import { scrape as scrapeLidl }    from "./lib/retailers/lidl_lv.mjs";
import { scrape as scrapeMego }    from "./lib/retailers/mego.mjs";
import { scrape as scrapeElvi }    from "./lib/retailers/elvi.mjs";

// National cage-free production-capacity share, Latvia 2026: cage-free 2,148,753
// of 4,596,707 laying-hen places = 46.7% ~ 0.47 (Eglitis & Kanepajs 2026). Used
// to weight unlabelled SKUs. Production-capacity proxy, not a retail volume share.
const ANCHOR = 0.47;

function defaultTag(d = new Date()) {
  const y = d.getFullYear();
  const q = Math.floor(d.getMonth() / 3) + 1;
  return `${y}-Q${q}-LV`;
}

// Pack price in EUR from a "1.99 EUR" style string. Captures the full numeric
// token (any number of decimals) and rounds to cents, rather than truncating.
function parsePriceEur(text) {
  const m = String(text || "").match(/(\d+(?:[.,]\d+)?)/);
  if (!m) return null;
  const v = Number(m[1].replace(",", "."));
  return Number.isFinite(v) ? Math.round(v * 100) / 100 : null;
}
// Eggs per pack from the listing name: "10gab.", "12 gab", "6gab.", "15 gab.", "10 gb."
function packCount(name) {
  const m = String(name || "").match(/(\d+)\s*(?:gab|gb)\b/i);
  return m ? Number(m[1]) : null;
}
function median(arr) {
  if (!arr.length) return null;
  const s = [...arr].sort((a, b) => a - b);
  const k = Math.floor(s.length / 2);
  return s.length % 2 ? s[k] : (s[k - 1] + s[k]) / 2;
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

async function appendHistory(date, summaryRows) {
  const path = "data/history/history.json";
  let hist = [];
  try {
    hist = JSON.parse(await readFile(path, "utf8"));
  } catch (e) {
    // Only treat a missing file as empty history. A corrupt/unreadable existing
    // file must NOT be silently replaced (that would destroy the accumulated series).
    if (e.code !== "ENOENT") throw new Error(`history.json unreadable; refusing to overwrite: ${e.message}`);
  }
  const rec = { date, retailers: {} };
  for (const b of summaryRows) {
    if (!b.shell_egg_listings) continue;
    rec.retailers[b.retailer] = {
      n: b.shell_egg_listings,
      cage_free_share_strict_pct: b.cage_free_share_strict_pct,
      cage_free_share_anchor_pct: b.cage_free_share_anchor_pct,
      median_price_per_egg: b.median_price_per_egg,
    };
  }
  hist = hist.filter(h => h.date !== date); // upsert: one record per date
  hist.push(rec);
  hist.sort((a, b) => (a.date < b.date ? -1 : 1));
  await mkdir("data/history", { recursive: true });
  await writeFile(path, JSON.stringify(hist, null, 2), "utf8");
  console.log(`History: ${hist.length} dated snapshot(s) (latest ${date}).`);
}

async function main() {
  const tag = process.argv[2] || defaultTag();
  const runDate = process.argv[3] || new Date().toISOString().slice(0, 10);
  console.log(`Running Latvian scrape for ${tag} (history date ${runDate})`);

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
      console.log(`  ${label}: FAILED: ${e.message}`);
      all.push({ retailer: label, error: e.message });
    }
  }

  // Fail loudly if a real data retailer (not an external_only stub) threw. A
  // transient outage or page-structure change must NOT be silently committed as
  // a 0%/"no catalogue" row and a permanent gap in the history series: exit
  // non-zero and write nothing, so the daily CI run goes red and the prior
  // committed snapshot stays live until a human looks.
  const EXPECTED = ["Rimi", "Barbora"];
  const failedExpected = all.filter(r => r.error && EXPECTED.includes(r.retailer)).map(r => r.retailer);
  if (failedExpected.length) {
    console.error(`\nFATAL: expected retailer(s) failed: ${failedExpected.join(", ")}. Writing nothing; exiting non-zero.`);
    process.exitCode = 1;
    return;
  }

  for (const r of all) {
    if (r.error || r.source === "external_only") {
      r.eu_code = null; r.production_label = "n/a"; r.is_shell_egg = null;
      r.cage_free = null; r.classify_source = "n/a";
      r.price_eur = null; r.pack_count = null; r.price_per_egg = null;
      continue;
    }
    const c = classify(r);
    r.eu_code = c.code;
    r.classify_source = c.source;
    r.production_label = codeLabel(c.code);
    r.is_shell_egg = isShellEgg(r);
    r.cage_free = c.code === null ? null : isCageFree(c.code);
    r.price_eur = parsePriceEur(r.price_text);
    r.pack_count = packCount(r.name);
    r.price_per_egg = (r.price_eur != null && r.pack_count)
      ? Number((r.price_eur / r.pack_count).toFixed(4)) : null;
  }

  await mkdir("data/raw", { recursive: true });
  await mkdir("data/summary", { recursive: true });

  const cols = ["retailer", "source", "name", "price_text", "price_eur", "pack_count", "price_per_egg",
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
      cage_free_share_strict_pct: null,
      cage_free_share_anchor_pct: null,
      median_price_per_egg: null,
      _prices: [],
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
    if (r.price_per_egg != null) b._prices.push(r.price_per_egg);
  }
  for (const b of Object.values(byRetailer)) {
    if (b.shell_egg_listings) {
      b.cage_free_share_strict_pct = Math.round(100 * b.cage_free_listings / b.shell_egg_listings);
      b.cage_free_share_anchor_pct = Math.round(100 * (b.cage_free_listings + b.unknown * ANCHOR) / b.shell_egg_listings);
      const med = median(b._prices);
      b.median_price_per_egg = med != null ? Number(med.toFixed(4)) : null;
    }
    delete b._prices;
  }
  const summaryRows = Object.values(byRetailer);
  const sumCols = ["retailer", "total_listings", "shell_egg_listings", "organic", "free_range", "barn", "caged", "unknown", "cage_free_listings", "cage_free_share_strict_pct", "cage_free_share_anchor_pct", "median_price_per_egg", "note"];
  await writeFile(`data/summary/${tag}_summary.csv`, toCSV(summaryRows, sumCols), "utf8");
  await writeFile(`data/summary/${tag}_summary.json`, JSON.stringify(summaryRows, null, 2), "utf8");

  await appendHistory(runDate, summaryRows);

  console.log(`\nNational cage-free anchor: ${Math.round(ANCHOR * 100)}% (Latvia production capacity, Eglitis & Kanepajs 2026)`);
  console.log("Summary by retailer (chicken shell eggs only):");
  console.table(summaryRows.map(b => ({
    retailer: b.retailer,
    listings: b.shell_egg_listings,
    "0-org": b.organic, "1-free": b.free_range, "2-barn": b.barn, "3-cage": b.caged, "?": b.unknown,
    cf_strict: b.cage_free_share_strict_pct,
    cf_anchor: b.cage_free_share_anchor_pct,
    "med_eur/egg": b.median_price_per_egg,
  })));
}

await main();

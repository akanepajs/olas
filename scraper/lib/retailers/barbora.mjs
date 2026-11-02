// Barbora Latvia scraper (barbora.lv, Maxima Group's online grocery). The eggs
// category is publicly accessible and server-rendered. Since the 2026-10-28 site
// relaunch (Remix app, category URLs under /c/<shortId>/...) the product objects
// sit in the `window.__remixContext = { ... }` JSON, in a React Query cache entry
// whose data has an `inventories` array. Each object has `id`, `title`, `price`
// and `categoryPathUrl`. The production system is in the title (kūtī dētas /
// brīvi turētu / bio / eko). Before the relaunch the same objects were in a
// `window.b_productList = [ ... ]` array (versions/barbora_20261102v1.mjs).

const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36";
const CATEGORIES = [
  "https://barbora.lv/c/ATPC/piena-produkti-un-olas/olas",            // parent eggs category (complete)
  "https://barbora.lv/c/ZEX6/piena-produkti-un-olas/olas/vistu-olas", // chicken eggs subcategory (belt and braces)
];
const MARKER = "window.__remixContext = ";

// String-aware bracket scan from html[start] (an opening bracket): only count
// brackets OUTSIDE JSON string literals, so a stray bracket inside a product
// title cannot truncate the value. Returns the index just past the match.
function scanJsonEnd(html, start) {
  const open = html[start], close = open === "{" ? "}" : "]";
  let depth = 0, inStr = false, esc = false, j = start;
  for (; j < html.length; j++) {
    const c = html[j];
    if (inStr) {
      if (esc) esc = false;
      else if (c === "\\") esc = true;
      else if (c === '"') inStr = false;
      continue;
    }
    if (c === '"') inStr = true;
    else if (c === open) depth++;
    else if (c === close) { depth--; if (depth === 0) return j + 1; }
  }
  return j;
}

function extractProductList(html) {
  const i = html.indexOf(MARKER);
  if (i < 0) return [];
  const start = html.indexOf("{", i);
  if (start < 0) return [];
  let ctx;
  try { ctx = JSON.parse(html.slice(start, scanJsonEnd(html, start))); } catch (e) {
    console.error(`  Barbora: page-data JSON parse failed (${e.message})`);
    return [];
  }
  // Take the inventories from every route's query cache rather than one named
  // route, so a renamed route file does not break the scrape.
  const out = [];
  for (const route of Object.values(ctx?.state?.loaderData || {})) {
    for (const q of route?.dehydratedState?.queries || []) {
      const d = q?.state?.data;
      if (!Array.isArray(d?.inventories)) continue;
      if (typeof d.count === "number" && d.count > d.inventories.length) {
        console.error(`  Barbora: page lists ${d.inventories.length} of ${d.count} products (pagination not handled)`);
      }
      out.push(...d.inventories);
    }
  }
  return out;
}

// One-line description of a response that yielded no products, so a red CI run
// shows whether Barbora returned an error code, a block/challenge page, or a
// normal page without the product-list marker. For a refused request the
// Cloudflare headers say whether it was a challenge ("cf-mitigated: challenge")
// or a plain block, and the cf-ray id locates it in Cloudflare's logs.
function describe(url, status, html, headers) {
  const slug = url.replace("https://barbora.lv/", "");
  if (html == null) return typeof status === "number" ? `${slug}: HTTP ${status}` : `${slug}: ${status}`;
  const t = html.match(/<title>([^<]{0,80})/i);
  const marker = html.includes(MARKER) ? "marker present" : "no __remixContext marker";
  const cf = headers
    ? ["server", "cf-mitigated", "cf-ray"].filter(h => headers.get(h)).map(h => `${h}=${headers.get(h)}`).join(" ")
    : "";
  return `${slug}: HTTP ${status}, ${html.length} chars, ${marker}, title "${t ? t[1].trim() : ""}"${cf ? `, ${cf}` : ""}`;
}

// Fetch one category page and parse it, retrying when the response is not OK or
// yields no products. 2026-09-26: a single run got nothing from both pages while
// a re-run 8 minutes later (same runner type) got the usual 15 products; the
// old code discarded the HTTP status, so the cause was unrecoverable.
// 2026-10-02: Cloudflare answered 403 to all six GitHub-runner attempts over ~2
// minutes while the same request from a residential IP got 200, and a re-run
// ~20 minutes later succeeded. The body of a refused response is now read too,
// so the log shows what kind of refusal it was. Longer waits live in the
// workflow (daily-scrape.yml re-runs the whole scrape after 10 and 20 minutes).
async function fetchProducts(url, waits) {
  const tries = [];
  for (let attempt = 0; ; attempt++) {
    let status = "network error", html = null, headers = null, products = [];
    try {
      const r = await fetch(url, { headers: { "User-Agent": UA, "Accept-Language": "lv-LV,lv;q=0.9,en;q=0.8" } });
      status = r.status;
      headers = r.headers;
      html = await r.text();
      if (r.ok) products = extractProductList(html);
    } catch (e) { status = `network error (${e.message})`; }
    if (products.length) return { products, tries };
    tries.push(describe(url, status, html, headers));
    if (attempt >= waits.length) return { products, tries };
    await new Promise(res => setTimeout(res, waits[attempt]));
  }
}

export async function scrape({ waits = [15_000, 45_000] } = {}) {
  const out = [];
  const seen = new Set();
  const failures = [];
  for (const url of CATEGORIES) {
    const { products, tries } = await fetchProducts(url, waits);
    if (tries.length) console.log(`  Barbora: ${products.length ? "recovered after" : "gave up after"} ${tries.length} failed attempt(s): ${tries.join(" | ")}`);
    if (!products.length) failures.push(tries[tries.length - 1]);
    for (const p of products) {
      const id = p.id || p.title;
      if (!p.title || seen.has(id)) continue;
      seen.add(id);
      const price = p.price;
      out.push({
        retailer: "Barbora",
        source: "barbora_html",
        sku_id: `barbora_${id}`,
        product_id: id,
        name: p.title,
        price_text: price != null ? `${price} EUR` : "",
        unit_price: null,
        category_path: (p.categoryPathUrl || "").replace(/^c\/[^/]+\//, ""),
        tipo_produccion: "",
      });
    }
    await new Promise(res => setTimeout(res, 300));
  }
  if (out.length === 0) throw new Error(`Barbora: no products parsed after retries (${failures.join(" | ")})`);
  return out;
}

// Barbora Latvia scraper (barbora.lv, Maxima Group's online grocery). The eggs
// category is publicly accessible and server-rendered: the product objects are
// embedded in a `window.b_productList = [ ... ]` JSON array. Each object has
// `title`, `units[].price` and a category path. The production system is in the
// title (kūtī dētas / brīvi turētu / bio / eko). We parse the JSON array.

const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36";
const CATEGORIES = [
  "https://barbora.lv/piena-produkti-un-olas/olas",            // parent eggs category (complete)
  "https://barbora.lv/piena-produkti-un-olas/olas/vistu-olas", // chicken eggs subcategory (belt and braces)
];

function extractProductList(html) {
  const key = "window.b_productList = ";
  const i = html.indexOf(key);
  if (i < 0) return [];
  const start = html.indexOf("[", i);
  if (start < 0) return [];
  // String-aware bracket scan: only count [ ] that are OUTSIDE JSON string
  // literals, so a stray bracket inside a product title cannot truncate the array.
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
    else if (c === "[") depth++;
    else if (c === "]") { depth--; if (depth === 0) { j++; break; } }
  }
  try { return JSON.parse(html.slice(start, j)); } catch (e) {
    console.error(`  Barbora: product-list JSON parse failed (${e.message})`);
    return [];
  }
}

// One-line description of a response that yielded no products, so a red CI run
// shows whether Barbora returned an error code, a block/challenge page, or a
// normal page without the product-list marker.
function describe(url, status, html) {
  const slug = url.replace("https://barbora.lv/", "");
  if (html == null) return typeof status === "number" ? `${slug}: HTTP ${status}` : `${slug}: ${status}`;
  const t = html.match(/<title>([^<]{0,80})/i);
  const marker = html.includes("window.b_productList = ") ? "marker present" : "no b_productList marker";
  return `${slug}: HTTP ${status}, ${html.length} chars, ${marker}, title "${t ? t[1].trim() : ""}"`;
}

// Fetch one category page and parse it, retrying when the response is not OK or
// yields no products. 2026-09-26: a single run got nothing from both pages while
// a re-run 8 minutes later (same runner type) got the usual 15 products; the
// old code discarded the HTTP status, so the cause was unrecoverable.
async function fetchProducts(url, waits) {
  const tries = [];
  for (let attempt = 0; ; attempt++) {
    let status = "network error", html = null, products = [];
    try {
      const r = await fetch(url, { headers: { "User-Agent": UA, "Accept-Language": "lv-LV,lv;q=0.9,en;q=0.8" } });
      status = r.status;
      if (r.ok) { html = await r.text(); products = extractProductList(html); }
    } catch (e) { status = `network error (${e.message})`; }
    if (products.length) return { products, tries };
    tries.push(describe(url, status, html));
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
      const price = p.units && p.units[0] && p.units[0].price;
      out.push({
        retailer: "Barbora",
        source: "barbora_html",
        sku_id: `barbora_${id}`,
        product_id: id,
        name: p.title,
        price_text: price != null ? `${price} EUR` : "",
        unit_price: null,
        category_path: p.category_path_url || "",
        tipo_produccion: "",
      });
    }
    await new Promise(res => setTimeout(res, 300));
  }
  if (out.length === 0) throw new Error(`Barbora: no products parsed after retries (${failures.join(" | ")})`);
  return out;
}

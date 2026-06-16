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
  let depth = 0, j = start;
  for (; j < html.length; j++) {
    const c = html[j];
    if (c === "[") depth++;
    else if (c === "]") { depth--; if (depth === 0) { j++; break; } }
  }
  try { return JSON.parse(html.slice(start, j)); } catch { return []; }
}

export async function scrape() {
  const out = [];
  const seen = new Set();
  for (const url of CATEGORIES) {
    const r = await fetch(url, { headers: { "User-Agent": UA, "Accept-Language": "lv-LV,lv;q=0.9,en;q=0.8" } });
    if (!r.ok) continue;
    const html = await r.text();
    for (const p of extractProductList(html)) {
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
  if (out.length === 0) throw new Error("Barbora: no products parsed (page structure may have changed)");
  return out;
}

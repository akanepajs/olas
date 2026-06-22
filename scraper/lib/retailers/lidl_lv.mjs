// Lidl Latvia (lidl.lv). lidl.lv publishes its standard in-store assortment as an
// online catalogue (with prices) built on Nuxt: the eggs category page embeds a
// `__NUXT_DATA__` payload (a flat, reference-indexed array) holding the product
// objects. There is no separate purchase flow, but the listing + price data is
// fully machine-readable, so this is a real (if small) shelf-presence dataset.
//
// Lidl runs a deliberately limited assortment, so the egg category typically
// holds only a couple of own/select-brand lines. We read the category, resolve
// the Nuxt references, and emit one row per product with its pack price; the
// runner derives the per-egg price from the "N gab." pack size folded into the
// name. Lidl is intentionally NOT in the runner's fail-fast EXPECTED set: if this
// parser ever breaks, the daily run should still publish Rimi/Barbora and let
// Lidl's line gap, rather than freezing the whole site.

const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36";
// Eggs category ("Olas") under food and drinks.
const ROOT = "https://www.lidl.lv/c/lv-LV/edieni-un-dzerieni/s10068374?category.id=10096079";

export async function scrape() {
  const r = await fetch(ROOT, { headers: { "User-Agent": UA, "Accept-Language": "lv-LV,lv;q=0.9,en;q=0.8" } });
  if (!r.ok) throw new Error(`HTTP ${r.status} on Lidl eggs category`);
  const html = await r.text();

  const i = html.indexOf("__NUXT_DATA__");
  if (i < 0) throw new Error("Lidl: __NUXT_DATA__ payload not found");
  const start = html.indexOf(">", i) + 1;
  const end = html.indexOf("</script>", start);
  let arr;
  try { arr = JSON.parse(html.slice(start, end)); }
  catch (e) { throw new Error(`Lidl: __NUXT_DATA__ parse failed (${e.message})`); }

  // Nuxt flat payload: object values are indices into the top-level array.
  const deref = (v) => (Number.isInteger(v) && v >= 0 && v < arr.length) ? arr[v] : v;
  const isObj = (v) => v && typeof v === "object" && !Array.isArray(v);

  const out = [];
  const seen = new Set();
  for (const x of arr) {
    if (!isObj(x) || !Number.isInteger(x.canonicalPath)) continue;
    const path = deref(x.canonicalPath);
    if (typeof path !== "string" || !path.startsWith("/p/") || !("fullTitle" in x)) continue;
    if (seen.has(path)) continue;
    seen.add(path);

    const title = deref(x.fullTitle);
    let price = null, baseText = "";
    const pd = deref(x.price);
    if (isObj(pd)) {
      const p = deref(pd.price);
      if (typeof p === "number") price = p;
      const bp = deref(pd.basePrice);
      if (isObj(bp)) baseText = deref(bp.text) || "";
    }
    // Pack size ("10 gab.") lives in the price subtext, not the title; fold it into
    // the name so the runner's packCount() can derive the per-egg price.
    const pm = String(baseText).match(/(\d+)\s*gab/i);
    const pack = pm ? Number(pm[1]) : null;
    const name = (pack && !/gab/i.test(String(title))) ? `${title}, ${pack} gab.` : String(title);
    const id = path.split("/").pop().replace(/^p/, "");

    out.push({
      retailer: "Lidl",
      source: "lidl_html",
      sku_id: `lidl_${id}`,
      product_id: id,
      name,
      brand: "",
      price_text: price != null ? `${price} EUR` : "",
      unit_price: null,
      category_path: path,
      tipo_produccion: "",
    });
  }

  if (out.length === 0) throw new Error("Lidl: no egg products parsed (page structure may have changed)");
  return out;
}

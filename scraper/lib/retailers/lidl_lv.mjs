// Lidl Latvia (lidl.lv). lidl.lv publishes its standard in-store assortment as an
// online catalogue (with prices). The site was relaunched around 2026-07-07: the
// old locale-prefixed category URLs (/c/lv-LV/...) now redirect to locale-less
// paths, products are no longer server-rendered into the __NUXT_DATA__ payload
// (they load client-side via a ProductGridbox fragment), and the old eggs
// category id (10096079) is dead in the new taxonomy. What still works is the
// public search JSON API the fragment itself uses, so we query it for "olas"
// and keep the rows whose title is an egg product.
//
// Lidl runs a deliberately limited assortment, so the egg category typically
// holds only a couple of own/select-brand lines. Search returns loosely related
// products too (milk, butter, shrimp on a recent check), so a title filter is
// required, and a genuine all-eggs delisting is indistinguishable from a filter
// miss: both throw. Lidl is intentionally NOT in the runner's fail-fast EXPECTED
// set: if this parser ever breaks, the daily run should still publish
// Rimi/Barbora and let Lidl's line gap, rather than freezing the whole site.

const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36";
const API = "https://www.lidl.lv/q/api/search?q=olas&fetchsize=48&locale=lv_LV&assortment=LV&version=v2.0.0";

export async function scrape() {
  // The WAF intermittently answers 406 to a request that succeeds seconds later
  // with identical headers; one retry is enough to ride that out.
  let r = await fetch(API, { headers: { "User-Agent": UA, "Accept": "application/json", "Accept-Language": "lv-LV,lv;q=0.9,en;q=0.8" } });
  if (!r.ok) {
    await new Promise(res => setTimeout(res, 5000));
    r = await fetch(API, { headers: { "User-Agent": UA, "Accept": "application/json", "Accept-Language": "lv-LV,lv;q=0.9,en;q=0.8" } });
  }
  if (!r.ok) throw new Error(`HTTP ${r.status} on Lidl search API`);
  let d;
  try { d = await r.json(); }
  catch (e) { throw new Error(`Lidl: search API JSON parse failed (${e.message})`); }

  const items = Array.isArray(d.items) ? d.items : [];
  const out = [];
  const seen = new Set();
  for (const it of items) {
    if (it.resultClass !== "product") continue;
    const g = it.gridbox && it.gridbox.data;
    if (!g) continue;
    const title = String(g.fullTitle || g.title || "");
    // Keep only egg products: "olas"/"ola" as a word in the title. Search also
    // returns unrelated groceries for q=olas; those never carry the word.
    if (!/\bolas?\b/i.test(title)) continue;
    const path = String(g.canonicalPath || g.canonicalUrl || "");
    if (!path.startsWith("/p/") || seen.has(path)) continue;
    seen.add(path);

    let price = null, baseText = "";
    const pd = g.price;
    if (pd && typeof pd === "object") {
      if (typeof pd.price === "number") price = pd.price;
      if (pd.basePrice && typeof pd.basePrice === "object") baseText = String(pd.basePrice.text || "");
    }
    // Pack size ("10 gab.") lives in the price subtext, not the title; fold it into
    // the name so the runner's packCount() can derive the per-egg price.
    const pm = baseText.match(/(\d+)\s*gab/i);
    const pack = pm ? Number(pm[1]) : null;
    const name = (pack && !/gab/i.test(title)) ? `${title}, ${pack} gab.` : title;
    const id = path.split("/").pop().replace(/^p/, "");

    out.push({
      retailer: "Lidl",
      source: "lidl_api",
      sku_id: `lidl_${id}`,
      product_id: id,
      name,
      brand: (g.brand && g.brand.name) || "",
      price_text: price != null ? `${price} EUR` : "",
      unit_price: null,
      category_path: path,
      tipo_produccion: "",
    });
  }

  if (out.length === 0) throw new Error("Lidl: no egg products in search results (assortment gap or API/filter change)");
  return out;
}

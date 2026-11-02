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
//
// 2026-07-15: since ~2026-07-08 the WAF answers 406 to any request carrying an
// "Accept: application/json" header (the exact same URL returns 200 without it,
// verified from a residential IP), so no Accept header is sent. Independently,
// the relaunched catalogue holds only ~95 promotional products with no eggs at
// all (product sitemap has none; /h/olas/h10096079 renders "nekas netika
// atrasts"), so until Lidl relists eggs online this scraper reaches the API
// fine and then throws the "no egg products" error below by design.

const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36";
const API = "https://www.lidl.lv/q/api/search?q=olas&fetchsize=48&locale=lv_LV&assortment=LV&version=v2.1.0";

export async function scrape() {
  // The WAF also intermittently answers 406 to requests that succeed later with
  // identical headers, and the bad window can outlast a quick retry (observed:
  // two attempts 5 s apart both 406, fine a minute later). Back off in growing
  // steps before giving up.
  const HEADERS = { "User-Agent": UA, "Accept-Language": "lv-LV,lv;q=0.9,en;q=0.8" };
  let r = await fetch(API, { headers: HEADERS });
  for (const waitMs of [10_000, 20_000, 40_000]) {
    if (r.ok) break;
    await new Promise(res => setTimeout(res, waitMs));
    r = await fetch(API, { headers: HEADERS });
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

    let price = null, baseText = "", packText = "";
    const pd = g.price;
    if (pd && typeof pd === "object") {
      if (typeof pd.price === "number") price = pd.price;
      if (pd.basePrice && typeof pd.basePrice === "object") baseText = String(pd.basePrice.text || "");
      if (pd.packaging && typeof pd.packaging === "object") packText = String(pd.packaging.text || "");
    }
    // Pack size ("10 gab.") is not in the title; fold it into the name so the
    // runner's packCount() can derive the per-egg price. It used to be the whole
    // basePrice text. Since ~2026-08-29 (on some days) basePrice is the unit price
    // instead ("1 gab. = 0,17 €") and the pack size is in price.packaging.text;
    // reading the "1" from basePrice made the per-egg price equal the pack price.
    // So: packaging first, then the key-facts list, then basePrice only when it
    // is not a "1 gab. = ..." unit-price line.
    const keyfacts = String((g.keyfacts && g.keyfacts.description) || "").replace(/<[^>]+>/g, " ");
    const isUnitPrice = /=/.test(baseText);
    let pack = null;
    for (const t of [packText, keyfacts, isUnitPrice ? "" : baseText]) {
      const pm = t.match(/(\d+)\s*gab/i);
      if (pm) { pack = Number(pm[1]); break; }
    }
    // Cross-check against the unit price when Lidl gives one: pack x unit price
    // should be within a few cents of the pack price.
    const um = isUnitPrice && baseText.match(/=\s*(\d+(?:[.,]\d+)?)/);
    if (um && price != null) {
      const unit = Number(um[1].replace(",", "."));
      const implied = unit > 0 ? Math.round(price / unit) : null;
      if (pack == null) pack = implied;
      else if (implied && Math.abs(implied - pack) > 1) {
        console.error(`  Lidl: pack size ${pack} disagrees with unit price (${baseText}, implies ${implied}) for "${title}"`);
      }
    }
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

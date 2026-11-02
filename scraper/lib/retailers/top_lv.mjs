// top! Latvia (etop.lv). The page is an Angular Universal app; the products come
// from a POST API at https://etop.lv/v1/Products/GetTopProducts with a JSON body
// {"categoryCodes":["21"],"brands":[],"page":1,"pageSize":N} (21 = eggs). A plain
// POST without the session XSRF token returned 200 on 2026-11-02.
//
// etop.lv is TOP's own-brand ("TIP TOP") showcase, not a full online grocery:
// the eggs category returns one own-brand product (TIP TOP barn eggs, EU code 2;
// totalCount=1, hasMore=false), while top! stores likely stock other brands too.
// Until 2026-11-02 top! was excluded for that reason. It is now included like
// Lidl (also one SKU online), with the page saying the figures rest on a single
// own-brand product (Art's decision, 2026-11-02). Like Lidl, top! is NOT in the
// runner's fail-fast EXPECTED set, so a failure here leaves a gap instead of
// freezing the whole site.

const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36";
const API = "https://etop.lv/v1/Products/GetTopProducts";
const EGG_CATEGORY = "21";
const PAGE_SIZE = 100;

async function fetchPage(page) {
  const body = JSON.stringify({ categoryCodes: [EGG_CATEGORY], brands: [], page, pageSize: PAGE_SIZE });
  const headers = { "User-Agent": UA, "Content-Type": "application/json", "Accept-Language": "lv-LV,lv;q=0.9,en;q=0.8" };
  let r = await fetch(API, { method: "POST", headers, body });
  for (const waitMs of [10_000, 20_000]) {
    if (r.ok) break;
    await new Promise(res => setTimeout(res, waitMs));
    r = await fetch(API, { method: "POST", headers, body });
  }
  if (!r.ok) throw new Error(`HTTP ${r.status} on top! GetTopProducts`);
  try { return await r.json(); }
  catch (e) { throw new Error(`top!: GetTopProducts JSON parse failed (${e.message})`); }
}

export async function scrape() {
  const out = [];
  const seen = new Set();
  for (let page = 1; page <= 10; page++) {
    const d = await fetchPage(page);
    for (const p of Array.isArray(d.list) ? d.list : []) {
      const id = p.code || p.keyCode || p.id;
      if (!p.name || seen.has(id)) continue;
      seen.add(id);
      out.push({
        retailer: "top!",
        source: "top_api",
        sku_id: `top_${id}`,
        product_id: id,
        name: p.name,
        brand: p.brand || "",
        price_text: typeof p.price === "number" ? `${p.price} EUR` : "",
        unit_price: typeof p.unitPrice === "number" ? p.unitPrice : null,
        category_path: p.parentKeyCode || "",
        tipo_produccion: "",
      });
    }
    if (!d.hasMore) break;
  }
  if (out.length === 0) throw new Error("top!: no products in the eggs category (assortment gap or API change)");
  return out;
}

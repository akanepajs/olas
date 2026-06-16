// Rimi Latvia scraper (rimi.lv e-veikals). The eggs category is publicly
// accessible without login and is server-rendered. Each product card carries a
// `data-gtm-eec-product='{"id","name","price",...}'` JSON attribute; the
// production system is in the product name, either as the EU code digit
// ("Nr.0/1/2/3") and/or a Latvian keyword (kūtī dētas, sprostos, brīvās
// turēšanas, eko/bio). We parse those JSON blobs directly.

const UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36";
// "Olas" (eggs) category. pageSize=99 to surface the whole category on one page.
const ROOT = "https://www.rimi.lv/e-veikals/lv/produkti/piena-produkti-un-olas/olas/c/SH-11-6?pageSize=99";

export async function scrape() {
  const r = await fetch(ROOT, { headers: { "User-Agent": UA, "Accept-Language": "lv-LV,lv;q=0.9,en;q=0.8" } });
  if (!r.ok) throw new Error(`HTTP ${r.status} on Rimi eggs category`);
  const html = await r.text();

  const out = [];
  const seen = new Set();
  // data-gtm-eec-product='{"id":"812416","name":"Olas ... Nr.3 ...","price":1.99,...}'
  const re = /data-gtm-eec-product='([^']+)'/g;
  let m;
  while ((m = re.exec(html))) {
    let p;
    try { p = JSON.parse(m[1]); } catch { continue; }
    if (!p || !p.name || seen.has(p.id)) continue;
    seen.add(p.id);
    out.push({
      retailer: "Rimi",
      source: "rimi_html",
      sku_id: `rimi_${p.id}`,
      product_id: p.id,
      name: p.name,
      brand: p.brand || "",
      price_text: p.price != null ? `${p.price} ${p.currency || "EUR"}` : "",
      unit_price: null,
      category_code: p.category || "",
      tipo_produccion: "",
    });
  }
  if (out.length === 0) throw new Error("Rimi: no products parsed (page structure may have changed)");
  return out;
}

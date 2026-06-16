// Elvi (elvi.lv). Elvi is a Latvian grocery chain whose website is a WordPress
// catalogue/promo site. It has an eggs page (elvi.lv/produkti/olas/), but the
// page lists no shoppable products with prices or housing labels (only WebSite
// schema and navigation; the eggs archive renders no product cards). No
// listing-level egg data is available online.

export async function scrape() {
  return [{
    retailer: "Elvi",
    source: "external_only",
    name: null,
    note: "Elvi (elvi.lv) eggs page lists no shoppable products (WordPress promo/catalogue site); no listing-level data.",
  }];
}

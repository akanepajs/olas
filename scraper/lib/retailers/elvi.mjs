// Elvi (elvi.lv). Elvi is a Latvian grocery chain whose website is a WordPress
// catalogue/promo site. Its eggs page (elvi.lv/produkti/olas/) is a single
// promo-leaflet product, checked 2026-11-02: "OLAS, Balticovo; 18 gab;
// 0,17€/gab", marked "Akcijas ir noslēgusies" (promotion ended), with no date,
// no pack price and no housing type. Balticovo sells more than one housing type
// (barn and free-range both listed at Rimi), so the entry cannot be classified and is not counted; the page names it
// as an expired, unclassifiable promo item.

export async function scrape() {
  return [{
    retailer: "Elvi",
    source: "external_only",
    name: null,
    note: "Elvi (elvi.lv) eggs page shows only one expired promo item (Balticovo, 18 eggs, 0.17 EUR/egg, undated) with no housing type, so it cannot be classified and is not counted.",
  }];
}

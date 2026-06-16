// top! Latvia (etop.lv). top! runs a transactional online store, but it is an
// Angular single-page app whose catalogue is served by an authenticated JSON API
// under https://etop.lv/v1/. The legacy OpenCart `index.php?route=product/...`
// endpoints return a blank PHP stub for every client (browser fetch included),
// and the /v1 product-search endpoint did not respond to standard GET/POST
// probes or to the in-app search in this pass. So no listing-level capture was
// obtained. A manual browser snapshot (open the eggs category in a logged-in
// session and dump the rendered product list to data/top_snapshot_<tag>.json)
// is the practical route if top! is needed in a future run.

export async function scrape() {
  return [{
    retailer: "top!",
    source: "external_only",
    name: null,
    note: "top! (etop.lv) online catalogue is an Angular SPA behind a /v1 JSON API; egg listings not machine-retrievable in this pass. No listing-level data captured.",
  }];
}

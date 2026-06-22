// top! Latvia (etop.lv). The catalogue IS machine-readable: the page is an
// Angular Universal app whose SSR HTML embeds an `ng-state` TransferState blob,
// and the products come from a POST API at https://etop.lv/v1/Products/GetTopProducts
// with a JSON body {"categoryCodes":["21"],"brands":[],"page":1,"pageSize":N}.
//
// But etop.lv is TOP's own-brand ("TIP TOP") showcase, not a full online grocery:
// the eggs category (`top-products-page`) returns exactly one own-brand product
// (TIP TOP barn eggs, EU code 2, about 0.30 EUR/egg; totalCount=1, hasMore=false).
// A single own-brand SKU is not comparable to Rimi's / Barbora's full assortments,
// so top! is deliberately excluded from the cage-free comparison (this is a scope
// decision, not an access failure). If a full TOP assortment ever appears here,
// POST the GetTopProducts endpoint with the session XSRF token and ingest `.list`.

export async function scrape() {
  return [{
    retailer: "top!",
    source: "external_only",
    name: null,
    note: "top! (etop.lv) is TOP's own-brand (TIP TOP) showcase, not a full online grocery: the eggs section has only one own-brand product (TIP TOP barn eggs, EU code 2, about 0.30 EUR/egg), so it is not comparable to a full assortment and is excluded.",
  }];
}

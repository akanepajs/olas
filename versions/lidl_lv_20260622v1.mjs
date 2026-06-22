// Lidl Latvia (lidl.lv). Lidl does not operate an online grocery store in
// Latvia: lidl.lv is a marketing / weekly-flyer ("Lidl Leták") site with no
// shoppable catalogue and no fresh shell-egg listings. Listing-level capture is
// not possible online; the in-store weekly flyer would be the only route.

export async function scrape() {
  return [{
    retailer: "Lidl",
    source: "external_only",
    name: null,
    note: "Lidl Latvia (lidl.lv) has no online grocery store (marketing/flyer site only); no online shell-egg listings.",
  }];
}

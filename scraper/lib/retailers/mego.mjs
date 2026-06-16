// Mego (mego.lv). Mego is a domestic Latvian grocery chain with no online store:
// mego.lv is an informational site (about / FAQ / store locator), with no
// shopping cart and no product catalogue (category paths such as /produkti/olas/
// return 404). No listing-level egg data is available online.

export async function scrape() {
  return [{
    retailer: "Mego",
    source: "external_only",
    name: null,
    note: "Mego (mego.lv) has no online store (informational site only); no egg catalogue.",
  }];
}

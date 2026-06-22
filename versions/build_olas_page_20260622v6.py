"""Build the two single-language pages for the cage-free Latvian eggs site.

Latvian -> index.html (served at olas.kanepajs.eu)
English -> index_en.html (mirrored to eggs.kanepajs.eu by the eggs repo)

Each page is fully self-contained (its own figures embedded as base64) and links
to the other language on its own domain. Numbers come from the scraper summary
JSON and the daily history JSON so the text matches the data exactly. Reuses the
euff.kanepajs.eu CSS scaffold. No em dashes (outward-facing, Art's name).

Usage:
    python scripts/build_olas_page.py 2026-Q2-LV /path/to/olas_site
    (olas_dir defaults to the repo root, i.e. this script's parent's parent)
"""

from __future__ import annotations

import base64
import json
import sys
from datetime import date
from pathlib import Path

NATIONAL_CF_PCT = 47
REPO_URL = "https://github.com/akanepajs/olas"
DATA_HISTORY_URL = "https://github.com/akanepajs/olas/blob/main/scraper/data/history/listings_history.json"
OLAS_URL = "https://olas.kanepajs.eu"
EGGS_URL = "https://eggs.kanepajs.eu"
LV_REPORT_URL = "https://www.dzivniekubriviba.lv/assets/downloadable-assets/ekonomiska-analize-par-dejejvistu-sprostu-aizlieguma-ietekmi-latvija.pdf"
EU_STANDARDS_URL = "https://agriculture.ec.europa.eu/farming/animal-products/eggs_en"
RETAILER_ORDER = ["Rimi", "Barbora", "Lidl"]

# Online catalogues the scraper reads (the actual scraped sources, surfaced as
# clickable links on the page).
SOURCE_URLS = {
    "Rimi": "https://www.rimi.lv/e-veikals/lv/produkti/piena-produkti-un-olas/olas/c/SH-11-6",
    "Barbora": "https://barbora.lv/piena-produkti-un-olas/olas",
}

LV_NOTES = {
    "top!": "top! (etop.lv) ir TOP pašu zīmola (TIP TOP) produktu vietne, nevis pilns interneta veikals: olu sadaļā ir tikai viens pašu zīmola produkts (TIP TOP kūtī dētas, ES kods 2, aptuveni 0.30 €/ola), tāpēc tas nav salīdzināms ar pilnu sortimentu un nav iekļauts.",
    "Mego": "Mego (mego.lv) nav tiešsaistes veikala (tikai informatīva lapa); olu kataloga nav.",
    "Elvi": "Elvi (elvi.lv) olu lapā nav pērkamu produktu (WordPress informatīva/akciju lapa); pozīciju nav.",
}

# English note overrides (others fall back to the scraper stub's `note`).
EN_NOTES = {
    "top!": "top! (etop.lv) is TOP's own-brand (TIP TOP) showcase, not a full online grocery: the eggs section has only one own-brand product (TIP TOP barn eggs, EU code 2, about 0.30 EUR/egg), so it is not comparable to a full assortment and is excluded.",
}

CSS = """<style>
  :root {
    --teal: #88a8a8; --olive: #889880; --pink: #c890a0; --ochre: #e0c868;
    --mint: #c8e8e0; --sage: #c0d0a9; --burgundy: #744c5b;
    --text: #36453e; --muted: #6a7a72; --grid: #dddddd; --bg: #fafaf8; --card: #ffffff;
  }
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body {
    font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    color: var(--text); background: var(--bg); line-height: 1.55;
    padding: 2rem 1rem; max-width: 960px; margin: 0 auto;
  }
  h1 { font-size: 1.55rem; font-weight: 700; margin-bottom: 0.3rem; }
  .subtitle { color: var(--muted); font-size: 0.95rem; margin-bottom: 1rem; }
  h2 { font-size: 1.15rem; font-weight: 600; margin: 2.2rem 0 0.8rem; padding-bottom: 0.3rem; border-bottom: 2px solid var(--teal); }
  p, li { font-size: 0.92rem; margin-bottom: 0.6rem; }
  ul { padding-left: 1.3rem; margin-bottom: 1rem; }
  a { color: var(--burgundy); }
  .key-message {
    background: var(--mint); border-left: 4px solid var(--teal);
    padding: 1rem 1.2rem; border-radius: 0 6px 6px 0; margin: 1.2rem 0; font-size: 0.95rem;
  }
  .key-message strong { display: block; margin-bottom: 0.3rem; }
  figure { margin: 1.4rem 0; }
  figure img { width: 100%; height: auto; border: 1px solid var(--grid); border-radius: 6px; background: #fff; }
  figcaption { color: var(--muted); font-size: 0.82rem; margin-top: 0.4rem; }
  table.data { border-collapse: collapse; width: 100%; font-size: 0.86rem; margin: 0.8rem 0 1.2rem; }
  table.data th, table.data td { border: 1px solid var(--grid); padding: 0.4rem 0.6rem; text-align: center; }
  table.data th { background: var(--sage); font-weight: 600; }
  table.data td:first-child, table.data th:first-child { text-align: left; }
  .lang-toggle { margin-bottom: 1.4rem; }
  .lang-toggle a {
    display: inline-block; font-size: 0.85rem; padding: 0.35rem 0.9rem; margin-right: 0.4rem;
    border: 1px solid var(--teal); background: #fff; color: var(--text); border-radius: 4px; text-decoration: none;
  }
  .lang-toggle a.active { background: var(--teal); color: #fff; }
  .disclosure { color: var(--muted); font-size: 0.8rem; border-top: 1px solid var(--grid); margin-top: 2.2rem; padding-top: 0.8rem; }
</style>"""


def listing_rows(rows):
    out = [r for r in rows if (r.get("shell_egg_listings") or 0) > 0]
    out.sort(key=lambda r: r["shell_egg_listings"], reverse=True)
    return out


def stub_rows(rows):
    return [r for r in rows if (r.get("shell_egg_listings") or 0) == 0]


def fmt_eur(v):
    return f"{v:.2f}" if v is not None else "-"


def table_html(rows, lang):
    head_lv = ["Tirgotājs", "SKU (n)", "Bioloģiskās", "Brīvās", "Kūtī", "Sprostos", "Bezsprostu %", "Mediānā €/ola"]
    head_en = ["Retailer", "SKUs (n)", "Organic", "Free-range", "Barn", "Caged", "Cage-free %", "Median €/egg"]
    head = head_lv if lang == "lv" else head_en
    th = "".join(f"<th>{h}</th>" for h in head)
    body = []
    for r in rows:
        strict = r["cage_free_share_strict_pct"]
        anchor = r["cage_free_share_anchor_pct"]
        cf = f"{strict}%" if anchor == strict else f"{strict}% ({anchor}%)"
        body.append(
            "<tr>"
            f"<td>{r['retailer']}</td>"
            f"<td>{r['shell_egg_listings']}</td>"
            f"<td>{r['organic']}</td>"
            f"<td>{r['free_range']}</td>"
            f"<td>{r['barn']}</td>"
            f"<td>{r['caged']}</td>"
            f"<td><strong>{cf}</strong></td>"
            f"<td>{fmt_eur(r.get('median_price_per_egg'))}</td>"
            "</tr>"
        )
    return f"<table class='data'><thead><tr>{th}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def stub_list_html(rows, lang):
    items = []
    for r in rows:
        if lang == "lv":
            note = LV_NOTES.get(r["retailer"], r.get("note", ""))
        else:
            note = EN_NOTES.get(r["retailer"], r.get("note", ""))
        items.append(f"<li><strong>{r['retailer']}</strong>: {note}</li>")
    return "<ul>" + "".join(items) + "</ul>"


def source_links_li(lang):
    links = ", ".join(f'<a href="{url}">{name}</a>' for name, url in SOURCE_URLS.items())
    label = "Iegūtie tiešsaistes katalogi" if lang == "lv" else "Scraped online catalogues"
    return f"<li>{label}: {links}.</li>"


def history_table_html(history, retailers, lang):
    date_h = "Datums" if lang == "lv" else "Date"
    sub = (["n", "Bezspr. %", "€/ola"] if lang == "lv" else ["n", "Cage-free %", "€/egg"])
    top = f"<th rowspan='2'>{date_h}</th>" + "".join(f"<th colspan='3'>{r}</th>" for r in retailers)
    second = "".join("".join(f"<th>{s}</th>" for s in sub) for _ in retailers)
    rows_html = []
    for rec in sorted(history, key=lambda h: h["date"], reverse=True):
        cells = [f"<td>{rec['date']}</td>"]
        for r in retailers:
            d = rec.get("retailers", {}).get(r)
            if d:
                cells.append(f"<td>{d['n']}</td><td>{d['cage_free_share_strict_pct']}%</td><td>{fmt_eur(d.get('median_price_per_egg'))}</td>")
            else:
                cells.append("<td>-</td><td>-</td><td>-</td>")
        rows_html.append("<tr>" + "".join(cells) + "</tr>")
    return f"<table class='data'><thead><tr>{top}</tr><tr>{second}</tr></thead><tbody>{''.join(rows_html)}</tbody></table>"


def page_shell(lang, title, body):
    lv_active = "active" if lang == "lv" else ""
    en_active = "active" if lang == "en" else ""
    return (
        "<!DOCTYPE html>\n"
        f'<html lang="{lang}">\n<head>\n'
        '<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
        f"<title>{title}</title>\n"
        + CSS + "\n</head>\n<body>\n\n"
        '<div class="lang-toggle">\n'
        f'  <a href="{OLAS_URL}" class="{lv_active}">Latviski</a>\n'
        f'  <a href="{EGGS_URL}" class="{en_active}">English</a>\n'
        "</div>\n"
        + body
        + "\n</body>\n</html>\n"
    )


def build(tag, olas_dir):
    root = Path(__file__).resolve().parent.parent
    summary = json.loads((root / "scraper" / "data" / "summary" / f"{tag}_summary.json").read_text(encoding="utf-8"))
    hist_path = root / "scraper" / "data" / "history" / "history.json"
    history = json.loads(hist_path.read_text(encoding="utf-8")) if hist_path.exists() else []
    data_date = max((h["date"] for h in history), default=date.today().isoformat())

    def b64(name):
        return base64.b64encode((root / name).read_bytes()).decode("ascii")

    # Latvian variants keep the base filename; English variants carry _en.
    b64_mix_lv = b64(f"fig_lv_listings_mix_{tag}.png")
    b64_mix_en = b64(f"fig_lv_listings_mix_en_{tag}.png")
    b64_price_lv = b64(f"fig_lv_price_per_egg_{tag}.png")
    b64_price_en = b64(f"fig_lv_price_per_egg_en_{tag}.png")

    lrows = listing_rows(summary)
    srows = stub_rows(summary)
    lk = {r["retailer"]: r for r in summary}
    rimi_cf = lk.get("Rimi", {}).get("cage_free_share_strict_pct", "n/a")
    barb_cf = lk.get("Barbora", {}).get("cage_free_share_strict_pct", "n/a")
    rimi_med = fmt_eur(lk.get("Rimi", {}).get("median_price_per_egg"))
    barb_med = fmt_eur(lk.get("Barbora", {}).get("median_price_per_egg"))

    table_lv, table_en = table_html(lrows, "lv"), table_html(lrows, "en")
    stubs_lv, stubs_en = stub_list_html(srows, "lv"), stub_list_html(srows, "en")
    hist_retailers = [r for r in RETAILER_ORDER if any(r in h.get("retailers", {}) for h in history)]
    hist_lv = history_table_html(history, hist_retailers, "lv")
    hist_en = history_table_html(history, hist_retailers, "en")
    src_lv, src_en = source_links_li("lv"), source_links_li("en")

    body_lv = f"""  <h1>Bezsprostu olu īpatsvars Latvijas mazumtirgotāju sortimentā</h1>
  <div class="subtitle">Tiešsaistes veikalu sortimenta uzskaite pa SKU. Pēdējie dati: {data_date} (atjaunināts katru dienu).</div>

  <div class="key-message">
    <strong>Galvenais secinājums</strong>
    Latvijas lielākie tiešsaistes pārtikas veikali pēc sortimenta vienību (SKU) skaita piedāvā gandrīz tikai bezsprostu olas: Rimi {rimi_cf}%, Barbora (Maxima) {barb_cf}%. Tas ir krietni virs valsts ražošanas bezsprostu īpatsvara (aptuveni {NATIONAL_CF_PCT}% no dējējvistu vietām; Eglītis un Kaņepājs, 2026). Šis ir pieejamības (plauktu klātbūtnes) rādītājs, nevis pārdošanas apjoma īpatsvars.
  </div>

  <figure>
    <img alt="Bezsprostu olu īpatsvars Latvijas veikalos" src="data:image/png;base64,{b64_mix_lv}">
    <figcaption>ES ražošanas kodu sadalījums pa tirgotājiem (0 bioloģiskās, 1 brīvās turēšanas, 2 kūtī dētas, 3 sprostos). Pārtrauktā līnija: valsts ražošanas bezsprostu īpatsvars aptuveni {NATIONAL_CF_PCT}%.</figcaption>
  </figure>

  {table_lv}

  <h2>Cena par olu</h2>
  <p>Cena par olu (pakas cena dalīta ar olu skaitu pakā, lai 6 un 10 olu iepakojumi būtu salīdzināmi). Sprostos dētas olas ir lētākās; bioloģiskās dārgākās. Mediānā: Rimi {rimi_med} €/olu, Barbora {barb_med} €/olu.</p>
  <figure>
    <img alt="Olu cena pa tirgotājiem un turēšanas veidu" src="data:image/png;base64,{b64_price_lv}">
    <figcaption>Katrs punkts ir viens produkts; krāsa = turēšanas veids (tāda pati kā augšējā attēlā). Pelēkā svītra: tirgotāja mediānā.</figcaption>
  </figure>

  <h2>Metode</h2>
  <p>No katra tirgotāja tiešsaistes kataloga tika nolasītas visas vistu (čaumalas) olu pozīcijas un katra klasificēta pēc ES ražošanas koda (0 bioloģiskās, 1 brīvās turēšanas, 2 kūtī dētas, 3 sprostos), izmantojot olu marķējuma kodu (Nr.0/1/2/3) un/vai atslēgvārdus produkta nosaukumā (kūtī dētas, sprostos, brīvās turēšanas, eko/bio). Paipalu olas un olu produkti (olu baltums u.c.) izslēgti. <strong>Bezsprostu %</strong> = kodi 0/1/2 attiecībā pret visām vistu olu pozīcijām. Visām pozīcijām bija ražošanas marķējums (0 neklasificētu), tāpēc valsts īpatsvara korekcija rezultātu nemaina.</p>

  <h2>Sortimenta segums</h2>
  <p>No sešiem lielajiem tīkliem trīs ir mašīnlasāms tiešsaistes olu katalogs (Rimi, Barbora/Maxima un Lidl; Lidl piedāvā nelielu olu sortimentu). Pārējie:</p>
  {stubs_lv}

  <h2>Ierobežojumi</h2>
  <ul>
    <li>Šis ir plauktu klātbūtnes rādītājs pēc SKU skaita, nevis pārdošanas apjoma īpatsvars. Tirgotājs ar 90% bezsprostu SKU joprojām var pārdot daudz sprostos dētu olu, ja lētākās, liela apjoma olas ir sprostos dētas.</li>
    <li>{NATIONAL_CF_PCT}% atsauce ir ražošanas jaudas (dējējvistu vietu) īpatsvars, nevis mazumtirdzniecības apjoms.</li>
    <li>Cena ir norādītā cena (var ietvert akcijas) dalīta ar olu skaitu; nav svērta pēc pārdotā apjoma.</li>
  </ul>

  <h2>Avoti</h2>
  <ul>
    {src_lv}
    <li>Eglītis un Kaņepājs (2026), <a href="{LV_REPORT_URL}">Ekonomiskā analīze par dējējvistu sprostu aizlieguma ietekmi Latvijā</a> (valsts bezsprostu īpatsvars).</li>
    <li>Eiropas Komisija, <a href="{EU_STANDARDS_URL}">olu tirdzniecības standarti</a> (kodi 0/1/2/3).</li>
    <li>Kods un dati: <a href="{REPO_URL}">{REPO_URL}</a>.</li>
  </ul>

  <h2>Vēsture</h2>
  <p>Datu kopa tiek automātiski atjaunināta katru dienu. Tabulā zemāk ir kopsavilkums (bezsprostu % un mediānā cena par olu katram datumam). Pilnie produktu līmeņa dati par katru momentuzņēmumu (veikals, cena, olu veids katrai pozīcijai) ir lejupielādējami <a href="{DATA_HISTORY_URL}">kā JSON GitHub</a>.</p>
  {hist_lv}

  <div class="disclosure">Analīzei un teksta sagatavošanai izmantots Claude Code.</div>
"""

    body_en = f"""  <h1>Cage-free share of egg listings at Latvian retailers</h1>
  <div class="subtitle">Online catalogue snapshot by SKU. Latest data: {data_date} (updated daily).</div>

  <div class="key-message">
    <strong>Headline</strong>
    Latvia's large online grocers list almost only cage-free eggs by stock-keeping unit (SKU) count: Rimi {rimi_cf}%, Barbora (Maxima) {barb_cf}%. That is well above the national cage-free production share (about {NATIONAL_CF_PCT}% of laying-hen places; Eglitis and Kanepajs 2026). This is a shelf-presence indicator, not a sales-volume share.
  </div>

  <figure>
    <img alt="Cage-free share of egg listings at Latvian retailers" src="data:image/png;base64,{b64_mix_en}">
    <figcaption>EU production-code mix by retailer (0 organic, 1 free-range, 2 barn, 3 caged). Dashed line: national cage-free production share, about {NATIONAL_CF_PCT}%.</figcaption>
  </figure>

  {table_en}

  <h2>Price per egg</h2>
  <p>Price per egg (pack price divided by the number of eggs per pack, so 6- and 10-egg packs compare fairly). Caged eggs are the cheapest; organic the dearest. Medians: Rimi {rimi_med} EUR/egg, Barbora {barb_med} EUR/egg.</p>
  <figure>
    <img alt="Egg price by retailer and production system" src="data:image/png;base64,{b64_price_en}">
    <figcaption>Each point is one product; color = production system (same as the chart above). Grey dash: retailer median.</figcaption>
  </figure>

  <h2>Method</h2>
  <p>Every chicken shell-egg listing in each retailer's online catalogue was read and classified by EU production code (0 organic, 1 free-range, 2 barn, 3 caged), using the egg-marking code in the name (Nr.0/1/2/3) and/or production keywords (kuti detas = barn, sprostos = caged, brivas turesanas = free-range, eko/bio = organic). Quail eggs and egg products (egg white, etc.) were excluded. <strong>Cage-free %</strong> = codes 0/1/2 over all chicken shell-egg listings. Every listing carried a production label (0 unknowns), so the national-anchor adjustment leaves the figure unchanged.</p>

  <h2>Coverage</h2>
  <p>Of six large chains, three have a machine-readable online egg catalogue (Rimi, Barbora/Maxima, and Lidl; Lidl carries a small egg range). The others:</p>
  {stubs_en}

  <h2>Limitations</h2>
  <ul>
    <li>Shelf presence by SKU count, not sales volume. A retailer with 90% cage-free SKUs could still sell many caged eggs if the cheap, high-volume lines are caged.</li>
    <li>The {NATIONAL_CF_PCT}% reference is production capacity (laying-hen places), not retail volume.</li>
    <li>Price is the listed price (may include promotions) divided by egg count; not weighted by sales volume.</li>
  </ul>

  <h2>Sources</h2>
  <ul>
    {src_en}
    <li>Eglitis and Kanepajs (2026), <a href="{LV_REPORT_URL}">Economic analysis of a laying-hen cage ban in Latvia</a> (national cage-free share).</li>
    <li>European Commission, <a href="{EU_STANDARDS_URL}">egg marketing standards</a> (codes 0/1/2/3).</li>
    <li>Code and data: <a href="{REPO_URL}">{REPO_URL}</a>.</li>
  </ul>

  <h2>History</h2>
  <p>The dataset is refreshed automatically each day. The table below is a summary (cage-free % and median price per egg for each date). The full product-level data behind every snapshot (shop, price, egg type for each listing) is downloadable as <a href="{DATA_HISTORY_URL}">JSON on GitHub</a>.</p>
  {hist_en}

  <div class="disclosure">Claude Code used for analysis and drafting.</div>
"""

    html_lv = page_shell("lv", "Bezsprostu olu īpatsvars Latvijas veikalos", body_lv)
    html_en = page_shell("en", "Cage-free share of egg listings at Latvian retailers", body_en)

    olas_dir.mkdir(parents=True, exist_ok=True)
    (olas_dir / "index.html").write_text(html_lv, encoding="utf-8")
    (olas_dir / "index_en.html").write_text(html_en, encoding="utf-8")
    (olas_dir / "CNAME").write_text("olas.kanepajs.eu\n", encoding="utf-8")
    (olas_dir / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Wrote {olas_dir / 'index.html'} ({len(html_lv)} chars, LV)")
    print(f"Wrote {olas_dir / 'index_en.html'} ({len(html_en)} chars, EN)")


if __name__ == "__main__":
    tag = sys.argv[1] if len(sys.argv) > 1 else "2026-Q2-LV"
    default_dir = Path(__file__).resolve().parent.parent
    olas_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else default_dir
    build(tag, olas_dir)

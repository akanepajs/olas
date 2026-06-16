"""Build the self-contained bilingual (LV + EN) index.html for olas.kanepajs.eu.

Pulls the per-retailer numbers from the scraper summary JSON (so the page text
matches the data exactly) and embeds the figure PNG as a base64 data URI. Reuses
the euff.kanepajs.eu CSS scaffold. No em dashes (outward-facing, Art's name).

Usage:
    python scripts/build_olas_page.py 2026-Q2-LV /path/to/olas_site
"""

from __future__ import annotations

import base64
import json
import sys
from pathlib import Path

SCRAPE_DATE = "2026-06-16"
NATIONAL_CF_PCT = 47
REPO_URL = "https://github.com/akanepajs/spain-egg-retailer-cage-free"
LV_REPORT_URL = "https://www.dzivniekubriviba.lv/assets/downloadable-assets/ekonomiska-analize-par-dejejvistu-sprostu-aizlieguma-ietekmi-latvija.pdf"
EU_STANDARDS_URL = "https://agriculture.ec.europa.eu/farming/animal-products/eggs_en"

# Latvian translations of the external_only stub notes (keyed by retailer).
LV_NOTES = {
    "top!": "top! (etop.lv) tiešsaistes katalogs ir Angular lietotne aiz /v1 JSON saskarnes; olu pozīcijas šajā piegājienā nebija mašīnlasāmas.",
    "Lidl": "Lidl Latvijā (lidl.lv) nav tiešsaistes pārtikas veikala (tikai akciju/bukletu lapa); tiešsaistē olu pozīciju nav.",
    "Mego": "Mego (mego.lv) nav tiešsaistes veikala (tikai informatīva lapa); olu kataloga nav.",
    "Elvi": "Elvi (elvi.lv) olu lapā nav pērkamu produktu (WordPress informatīva/akciju lapa); pozīciju nav.",
}


def listing_rows(rows: list[dict]) -> list[dict]:
    out = [r for r in rows if (r.get("shell_egg_listings") or 0) > 0]
    out.sort(key=lambda r: r["shell_egg_listings"], reverse=True)
    return out


def stub_rows(rows: list[dict]) -> list[dict]:
    return [r for r in rows if (r.get("shell_egg_listings") or 0) == 0]


def table_html(rows: list[dict], lang: str) -> str:
    head_lv = ["Tirgotājs", "SKU (n)", "Bioloģiskās", "Brīvās", "Kūtī", "Sprostos", "Bezsprostu %"]
    head_en = ["Retailer", "SKUs (n)", "Organic", "Free-range", "Barn", "Caged", "Cage-free %"]
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
            "</tr>"
        )
    return f"<table class='data'><thead><tr>{th}</tr></thead><tbody>{''.join(body)}</tbody></table>"


def stub_list_html(rows: list[dict], lang: str) -> str:
    items = []
    for r in rows:
        note = LV_NOTES.get(r["retailer"], r.get("note", "")) if lang == "lv" else r.get("note", "")
        items.append(f"<li><strong>{r['retailer']}</strong>: {note}</li>")
    return "<ul>" + "".join(items) + "</ul>"


def build(tag: str, olas_dir: Path) -> None:
    root = Path(__file__).resolve().parent.parent
    summary = json.loads((root / "scraper" / "data" / "summary" / f"{tag}_summary.json").read_text(encoding="utf-8"))
    png = (root / f"fig_lv_listings_mix_{tag}.png").read_bytes()
    b64 = base64.b64encode(png).decode("ascii")
    quarter = tag.replace("-LV", "")

    lrows = listing_rows(summary)
    srows = stub_rows(summary)
    lk = {r["retailer"]: r for r in summary}
    rimi_cf = lk.get("Rimi", {}).get("cage_free_share_strict_pct", "n/a")
    barb_cf = lk.get("Barbora", {}).get("cage_free_share_strict_pct", "n/a")

    table_lv, table_en = table_html(lrows, "lv"), table_html(lrows, "en")
    stubs_lv, stubs_en = stub_list_html(srows, "lv"), stub_list_html(srows, "en")

    html = f"""<!DOCTYPE html>
<html lang="lv">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Bezsprostu olu īpatsvars Latvijas veikalos / Cage-free eggs in Latvian retail</title>
<style>
  :root {{
    --teal: #88a8a8; --olive: #889880; --pink: #c890a0; --ochre: #e0c868;
    --mint: #c8e8e0; --sage: #c0d0a9; --burgundy: #744c5b;
    --text: #36453e; --muted: #6a7a72; --grid: #dddddd; --bg: #fafaf8; --card: #ffffff;
  }}
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{
    font-family: 'Segoe UI', 'Helvetica Neue', Arial, sans-serif;
    color: var(--text); background: var(--bg); line-height: 1.55;
    padding: 2rem 1rem; max-width: 960px; margin: 0 auto;
  }}
  h1 {{ font-size: 1.55rem; font-weight: 700; margin-bottom: 0.3rem; }}
  .subtitle {{ color: var(--muted); font-size: 0.95rem; margin-bottom: 1rem; }}
  h2 {{ font-size: 1.15rem; font-weight: 600; margin: 2.2rem 0 0.8rem; padding-bottom: 0.3rem; border-bottom: 2px solid var(--teal); }}
  p, li {{ font-size: 0.92rem; margin-bottom: 0.6rem; }}
  ul {{ padding-left: 1.3rem; margin-bottom: 1rem; }}
  a {{ color: var(--burgundy); }}
  .key-message {{
    background: var(--mint); border-left: 4px solid var(--teal);
    padding: 1rem 1.2rem; border-radius: 0 6px 6px 0; margin: 1.2rem 0; font-size: 0.95rem;
  }}
  .key-message strong {{ display: block; margin-bottom: 0.3rem; }}
  figure {{ margin: 1.4rem 0; }}
  figure img {{ width: 100%; height: auto; border: 1px solid var(--grid); border-radius: 6px; background: #fff; }}
  figcaption {{ color: var(--muted); font-size: 0.82rem; margin-top: 0.4rem; }}
  table.data {{ border-collapse: collapse; width: 100%; font-size: 0.86rem; margin: 0.8rem 0 1.2rem; }}
  table.data th, table.data td {{ border: 1px solid var(--grid); padding: 0.4rem 0.6rem; text-align: center; }}
  table.data th {{ background: var(--sage); font-weight: 600; }}
  table.data td:first-child, table.data th:first-child {{ text-align: left; }}
  .lang-toggle {{ margin-bottom: 1.4rem; }}
  .lang-toggle button {{
    font: inherit; font-size: 0.85rem; padding: 0.35rem 0.9rem; margin-right: 0.4rem;
    border: 1px solid var(--teal); background: #fff; color: var(--text); border-radius: 4px; cursor: pointer;
  }}
  .lang-toggle button.active {{ background: var(--teal); color: #fff; }}
  .disclosure {{ color: var(--muted); font-size: 0.8rem; border-top: 1px solid var(--grid); margin-top: 2.2rem; padding-top: 0.8rem; }}
  [data-lang] {{ display: none; }}
  [data-lang].active {{ display: block; }}
</style>
</head>
<body>

<div class="lang-toggle">
  <button id="btn-lv" class="active" onclick="setLang('lv')">Latviski</button>
  <button id="btn-en" onclick="setLang('en')">English</button>
</div>

<!-- ===================== LATVIAN ===================== -->
<div data-lang="lv" class="active">
  <h1>Bezsprostu olu īpatsvars Latvijas mazumtirgotāju sortimentā</h1>
  <div class="subtitle">Tiešsaistes veikalu sortimenta uzskaite pa SKU, {quarter} (dati iegūti {SCRAPE_DATE})</div>

  <div class="key-message">
    <strong>Galvenais secinājums</strong>
    Latvijas lielākie tiešsaistes pārtikas veikali pēc sortimenta vienību (SKU) skaita piedāvā gandrīz tikai bezsprostu olas: Rimi {rimi_cf}%, Barbora (Maxima) {barb_cf}%. Tas ir krietni virs valsts ražošanas bezsprostu īpatsvara (aptuveni {NATIONAL_CF_PCT}% no dējējvistu vietām; Eglītis un Kaņepājs, 2026). Šis ir pieejamības (plauktu klātbūtnes) rādītājs, nevis pārdošanas apjoma īpatsvars.
  </div>

  <figure>
    <img alt="Bezsprostu olu īpatsvars Latvijas veikalos" src="data:image/png;base64,{b64}">
    <figcaption>ES ražošanas kodu sadalījums pa tirgotājiem (0 bioloģiskās, 1 brīvās turēšanas, 2 kūtī dētas, 3 sprostos). Pārtrauktā līnija: valsts ražošanas bezsprostu īpatsvars aptuveni {NATIONAL_CF_PCT}%.</figcaption>
  </figure>

  {table_lv}

  <h2>Metode</h2>
  <p>No katra tirgotāja tiešsaistes kataloga tika nolasītas visas vistu (čaumalas) olu pozīcijas un katra klasificēta pēc ES ražošanas koda (0 bioloģiskās, 1 brīvās turēšanas, 2 kūtī dētas, 3 sprostos), izmantojot olu marķējuma kodu (Nr.0/1/2/3) un/vai atslēgvārdus produkta nosaukumā (kūtī dētas, sprostos, brīvās turēšanas, eko/bio). Paipalu olas un olu produkti (olu baltums u.c.) izslēgti. <strong>Bezsprostu %</strong> = kodi 0/1/2 attiecībā pret visām vistu olu pozīcijām. Visām pozīcijām bija ražošanas marķējums (0 neklasificētu), tāpēc valsts īpatsvara korekcija rezultātu nemaina.</p>

  <h2>Sortimenta segums</h2>
  <p>No sešiem lielajiem tīkliem tikai diviem ir mašīnlasāms tiešsaistes olu katalogs (Rimi, Barbora/Maxima). Pārējie:</p>
  {stubs_lv}

  <h2>Ierobežojumi</h2>
  <ul>
    <li>Šis ir plauktu klātbūtnes rādītājs pēc SKU skaita, nevis pārdošanas apjoma īpatsvars. Tirgotājs ar 90% bezsprostu SKU joprojām var pārdot daudz sprostos dētu olu, ja lētākās, liela apjoma olas ir sprostos dētas.</li>
    <li>{NATIONAL_CF_PCT}% atsauce ir ražošanas jaudas (dējējvistu vietu) īpatsvars, nevis mazumtirdzniecības apjoms.</li>
    <li>Vienas dienas uzskaite; sortiments laika gaitā var mainīties.</li>
  </ul>

  <h2>Avoti</h2>
  <ul>
    <li>Eglītis un Kaņepājs (2026), <a href="{LV_REPORT_URL}">Ekonomiskā analīze par dējējvistu sprostu aizlieguma ietekmi Latvijā</a> (valsts bezsprostu īpatsvars).</li>
    <li>Eiropas Komisija, <a href="{EU_STANDARDS_URL}">olu tirdzniecības standarti</a> (kodi 0/1/2/3).</li>
    <li>Kods un dati: <a href="{REPO_URL}">{REPO_URL}</a>.</li>
  </ul>

  <div class="disclosure">Analīzei un teksta sagatavošanai izmantots Claude Code.</div>
</div>

<!-- ===================== ENGLISH ===================== -->
<div data-lang="en">
  <h1>Cage-free share of egg listings at Latvian retailers</h1>
  <div class="subtitle">Online catalogue snapshot by SKU, {quarter} (data collected {SCRAPE_DATE})</div>

  <div class="key-message">
    <strong>Headline</strong>
    Latvia's large online grocers list almost only cage-free eggs by stock-keeping unit (SKU) count: Rimi {rimi_cf}%, Barbora (Maxima) {barb_cf}%. That is well above the national cage-free production share (about {NATIONAL_CF_PCT}% of laying-hen places; Eglitis and Kanepajs 2026). This is a shelf-presence indicator, not a sales-volume share.
  </div>

  <figure>
    <img alt="Cage-free share of egg listings at Latvian retailers" src="data:image/png;base64,{b64}">
    <figcaption>EU production-code mix by retailer (0 organic, 1 free-range, 2 barn, 3 caged). Dashed line: national cage-free production share, about {NATIONAL_CF_PCT}%.</figcaption>
  </figure>

  {table_en}

  <h2>Method</h2>
  <p>Every chicken shell-egg listing in each retailer's online catalogue was read and classified by EU production code (0 organic, 1 free-range, 2 barn, 3 caged), using the egg-marking code in the name (Nr.0/1/2/3) and/or production keywords (kuti detas = barn, sprostos = caged, brivas turesanas = free-range, eko/bio = organic). Quail eggs and egg products (egg white, etc.) were excluded. <strong>Cage-free %</strong> = codes 0/1/2 over all chicken shell-egg listings. Every listing carried a production label (0 unknowns), so the national-anchor adjustment leaves the figure unchanged.</p>

  <h2>Coverage</h2>
  <p>Of six large chains, only two have a machine-readable online egg catalogue (Rimi, Barbora/Maxima). The others:</p>
  {stubs_en}

  <h2>Limitations</h2>
  <ul>
    <li>Shelf presence by SKU count, not sales volume. A retailer with 90% cage-free SKUs could still sell many caged eggs if the cheap, high-volume lines are caged.</li>
    <li>The {NATIONAL_CF_PCT}% reference is production capacity (laying-hen places), not retail volume.</li>
    <li>Single-day snapshot; assortment can change over time.</li>
  </ul>

  <h2>Sources</h2>
  <ul>
    <li>Eglitis and Kanepajs (2026), <a href="{LV_REPORT_URL}">Economic analysis of a laying-hen cage ban in Latvia</a> (national cage-free share).</li>
    <li>European Commission, <a href="{EU_STANDARDS_URL}">egg marketing standards</a> (codes 0/1/2/3).</li>
    <li>Code and data: <a href="{REPO_URL}">{REPO_URL}</a>.</li>
  </ul>

  <div class="disclosure">Claude Code used for analysis and drafting.</div>
</div>

<script>
  function setLang(l) {{
    document.querySelectorAll('[data-lang]').forEach(function (el) {{
      el.classList.toggle('active', el.getAttribute('data-lang') === l);
    }});
    document.getElementById('btn-lv').classList.toggle('active', l === 'lv');
    document.getElementById('btn-en').classList.toggle('active', l === 'en');
    document.documentElement.lang = l;
  }}
</script>
</body>
</html>
"""

    olas_dir.mkdir(parents=True, exist_ok=True)
    (olas_dir / "index.html").write_text(html, encoding="utf-8")
    (olas_dir / "CNAME").write_text("olas.kanepajs.eu\n", encoding="utf-8")
    (olas_dir / ".nojekyll").write_text("", encoding="utf-8")
    print(f"Wrote {olas_dir / 'index.html'} ({len(html)} chars, figure {len(b64)} b64 chars)")


if __name__ == "__main__":
    tag = sys.argv[1] if len(sys.argv) > 1 else "2026-Q2-LV"
    olas_dir = Path(sys.argv[2]) if len(sys.argv) > 2 else Path("olas_site")
    build(tag, olas_dir)

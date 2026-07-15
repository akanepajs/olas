# Latvian language and style guide for olas.kanepajs.eu

This site is generated daily and published under Art's name. The Latvian text is
not hand-edited on the page: it is regenerated every day by the build apparatus,
so every wording fix must be made in the SOURCE files below, or the next daily
build reintroduces the old text.

## Where the Latvian text lives (the only two files to edit)

- `scripts/make_figures_lv.py`: chart titles, axis labels, legends, annotations.
  All in the `STR["lv"]` dict near the top. This text is baked into the PNG, so a
  change is only visible after the figures are re-rendered.
- `scripts/build_olas_page.py`: all page prose (headings, paragraphs, table
  headers, the `LV_NOTES` retailer notes, figure `alt` / `figcaption` text, the
  disclosure line). Most of it sits inside the `body_lv` f-string.

Duplication trap: each figure title exists TWICE, once as the chart title in
`make_figures_lv.py` and once as the HTML `<img alt="...">` in
`build_olas_page.py`. Fix both or they drift apart.

Pipeline: `.github/workflows/daily-scrape.yml` runs the scraper, then
`make_figures_lv.py`, then `build_olas_page.py`, and commits the regenerated
`index.html` plus PNGs (commit message `Daily egg-listings update <date>`). To
see a source fix on the live site, re-run both Python scripts, or wait for the
next daily build (cron 05:30 UTC).

## Rules (from the language review of 2026-06-30)

### R1. "by category X" is `pēc` + genitive, not `pa` + dative
When a label means "broken down by / according to" a criterion, use `pēc` +
genitive. Reserve `pa` for distribution into parts; do not use it for a
classification criterion.
- Wrong: `Olu cena pa tirgotājiem un turēšanas veidu`. It mixes a dative plural
  (`tirgotājiem`) with an accusative singular (`veidu`) under one preposition,
  and `pa` is colloquial in this sense.
- Right: `Olu cena pēc tirgotāja un turēšanas veida`. Both nouns are genitive
  singular, one consistent government. (This is the fix applied on 2026-06-30.)
- Borderline: `sadalījums pa tirgotājiem` (distribution across retailers) is an
  accepted collocation, but prefer `pēc tirgotāja` for consistency on this site.

### R2. Simple prepositions take the dative in the plural
Every primary preposition governs the dative/instrumental in the plural, whatever
case it takes in the singular. So `attiecībā pret visām pozīcijām` (dative plural)
is CORRECT even though `pret` takes the accusative in the singular. Do not "fix"
these to the accusative.

### R3. Possession with a numeral uses a dative subject
"three [chains] have X" is `trim ir X`, not `trīs ir X`. The thing possessed
stays nominative; the possessor numeral goes to the dative.

### R4. Apposition labels stay nominative
In a "label: value" caption the value is nominative:
`Pelēkā svītra: tirgotāja mediāna` (not `mediānā`, which reads as a locative
"in the median").

### R5. `mediāna` vs `mediānā`: three distinct forms, do not mix by accident
- `mediāna`: the noun in the nominative (e.g. the chart annotation `mediāna 0.30`,
  or apposition `tirgotāja mediāna`).
- `mediānā`: adverbial "at the median" (`Mediānā €/ola`, `Mediānā: Rimi ...`) OR
  the definite adjective before a noun (`mediānā cena`). Both are fine in context.
- A bare `tirgotāja mediānā` with no following noun is the noun, so it must be
  `mediāna`.

### R6. Participle and adjective endings must agree with the real subject
Check that every `-ts / -ta / -ti / -tas` ending agrees with the noun it
describes. Correct examples already on the page: `cena ... dalīta`,
`kopa ... atjaunināta`, `dati ... lejupielādējami`. A floating
`(atjaunināts katru dienu)` has no clear masculine-singular antecedent; either
agree it with `dati` (masculine plural) as `atjaunināti`, or rephrase
impersonally as `(atjaunina katru dienu)`.

### R7. Keep units and terms internally consistent
Pick one form and use it everywhere:
- price unit: standardized on `€/olu` (after `par olu`, accusative) on 2026-06-30;
  previously the table header read `€/ola` while the body read `€/olu`.
- "by SKU": standardized on `pēc SKU` / `pēc SKU skaita`; the subtitle previously
  read `pa SKU`.

### R8. House rules that already hold (keep them)
- No em dashes anywhere (outward-facing, under Art's name). Use a middle dot,
  colon, comma, parentheses, or a sentence break.
- Numbers come from the data JSON, never typed by hand, so the text matches the
  data.
- LV goes to `index.html`, EN to `index_en.html`. The `LV_NOTES` dict overrides
  the scraper's English notes on the LV page, so Latvian retailer notes are fixed
  there.

## Review checklist before committing a Latvian wording change

1. Read the changed sentence aloud; does the case government hold end to end?
2. Does every participle/adjective agree with its noun (gender + number)?
3. Is a classification criterion expressed with `pēc` + genitive (R1)?
4. Did you change BOTH copies of a figure title (chart + `alt`)?
5. Are units/terms consistent with the rest of the page (R7)?
6. No em dashes.
7. Re-run `make_figures_lv.py` then `build_olas_page.py` and eyeball the PNG and
   `index.html` before relying on it.

## Issue log (review 2026-06-30)

| # | Location | Issue | Severity | Status |
|---|---|---|---|---|
| 1 | `price_title` in both source files | `pa tirgotājiem un turēšanas veidu` to `pēc tirgotāja un turēšanas veida` (R1) | high | FIXED 2026-06-30 |
| 2 | `build_olas_page.py` L243 (Sortimenta segums) | `trīs ir ... katalogs` to `trim ir ... katalogs` (R3) | med-high | FIXED 2026-06-30 |
| 3 | `build_olas_page.py` L236 (fig 2 caption) | `tirgotāja mediānā` to `tirgotāja mediāna` (R4) | med | FIXED 2026-06-30 |
| 4 | `build_olas_page.py` L219 (subtitle) | `(atjaunināts katru dienu)` to `(atjaunina katru dienu)` (R6) | med | FIXED 2026-06-30 |
| 5 | `build_olas_page.py` L262 (Vēsture) | `kā JSON GitHub` missing connector, e.g. `kā JSON GitHub vietnē` | med | FIXED 2026-06-30 |
| 6 | `build_olas_page.py` L42 (`LV_NOTES` top!) | `tas nav salīdzināms ... iekļauts` vs feminine `vietne`; optionally `tā ... salīdzināma ... iekļauta` | low | FIXED 2026-06-30 |
| 7 | site-wide | `€/ola` vs `€/olu`; `pa SKU` vs `pēc SKU skaita`; `sadalījums pa tirgotājiem` (R7) | consistency | FIXED 2026-06-30 |
| 8 | `make_figures_lv.py` L57 (legend) | `nezināms` (masc sg) vs other codes feminine plural | low | FIXED 2026-06-30 |

The rest of the page (key message, method, limitations, sources, history,
disclosure, and all `LV_NOTES`) reads as correct and idiomatic.

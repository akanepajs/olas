// EU egg-marking codes:
//   0 = organic, 1 = free-range, 2 = barn (cage-free indoor), 3 = caged
// The retailer-facing Spanish vocabulary maps to these codes.
// We classify in three passes: first by an explicit "tipo de producción" field
// if the source provides one; then by the EU production-code digit printed in
// the listing name (Latvian retailers write it as "Nr.0/1/2/3"); then by
// production-system keyword in the product name. Latvian vocabulary is added
// alongside the Spanish/Catalan so a single classifier serves both markets;
// the Latvian strings do not collide with the Spanish/Catalan ones.

const NAME_PATTERNS = [
  // Order matters: more specific patterns first.
  // Catalan vocab is included for Caprabo (Eroski Group's Catalonia banner).
  { code: 0, regex: /\b(eco|ecol[oó]gic|ecològic|biol[oó]gic|orgánic|viubio)/i, label: "organic" },
  { code: 0, regex: /\bbio\b/i, label: "organic" },
  { code: 1, regex: /\b(camper[oa]s?|camperol|caser[ií]o|free[\s-]?range)\b/i, label: "free-range" },
  { code: 2, regex: /\b(suelo|en suelo|criadas? en suelo|barn|gallinas en suelo|s[oò]l|terra)\b/i, label: "barn" },
  { code: 3, regex: /\b(jaula|jaulas acondicionadas|caged)\b/i, label: "caged" },
  // --- Latvian vocabulary (Rimi, Barbora/Maxima) ---
  // organic: bioloģiskās, eko, ekoloģisk-  (bio handled by the \bbio\b rule above)
  { code: 0, regex: /\b(biolo[gģ]isk|ekolo[gģ]isk|\beko\b)/i, label: "organic" },
  // free-range: brīvās turēšanas / brīvi turēt- / brīvos apstākļos / brīvā daba / "brīv.vis."
  { code: 1, regex: /br[iī]v(?:[aā]s? tur|i tur|os apst|[aā] dab|\.vis)/i, label: "free-range" },
  // barn / floor: kūtī dētas / kūtī / kūts / uz grīdas
  { code: 2, regex: /(k[uū]t[iī]\b|k[uū]t[iī] d[eē]t|\bk[uū]ts\b|uz gr[iī]das)/i, label: "barn" },
  // caged: sprostos / sprostā / sprostu / sprostos dētas / būros / būri
  { code: 3, regex: /(sprost\w*|\bb[uū]r[oiu]\w*)/i, label: "caged" },
];

const FIELD_MAP = {
  // Carrefour "Tipo de producción" field
  "ecológicos": 0, "ecológico": 0, "ecologicos": 0, "ecologico": 0, "bio": 0, "biológico": 0,
  "campero": 1, "camperos": 1, "campera": 1, "camperas": 1,
  "suelo": 2, "barn": 2, "sòl": 2, "terra": 2,
  "jaula": 3, "jaulas": 3, "caged": 3,
  // Latvian "Turēšanas veids" (housing type) field values
  "bioloģiskās": 0, "bioloģiska": 0, "ekoloģiskās": 0,
  "brīvās turēšanas": 1, "brīvi turētu": 1, "brīvā turēšana": 1,
  "kūtī dētas": 2, "kūtī": 2, "kūts": 2,
  "sprostos dētas": 3, "sprostos": 3, "sprostu": 3,
};

// EU production-code digit written in the listing name. Latvian retail packs
// carry the legal method code as "Nr.0/1/2/3" (or "No.2"); this is the
// authoritative housing signal and is checked before name keywords.
const EGG_CODE_DIGIT = /\bN[ro]\.?\s*([0-3])\b/i;

const CODE_LABEL = { 0: "organic", 1: "free-range", 2: "barn", 3: "caged" };

export function classify(product) {
  // product: { name, tipo_produccion?, ... }
  const rawTipo = (product.tipo_produccion || "").trim().toLowerCase();
  if (rawTipo && FIELD_MAP[rawTipo] !== undefined) {
    return { code: FIELD_MAP[rawTipo], source: "tipo_produccion_field", confidence: "high" };
  }
  const name = product.name || "";
  // Explicit production-system keyword first (sprostos / kūtī / brīvās / eko /
  // jaula / suelo ...). These are unambiguous, so they take precedence over a
  // bare "Nr.X / No.X" token, which can also appear as a marketing label
  // ("TOP No.1") rather than the legal egg code and would otherwise misclassify.
  for (const p of NAME_PATTERNS) {
    if (p.regex.test(name)) {
      return { code: p.code, source: "name_keyword", confidence: "medium" };
    }
  }
  // EU production-code digit in the name ("Nr.0/1/2/3"): used when no housing
  // keyword is present (common on Latvian packs that print only the code).
  const dm = name.match(EGG_CODE_DIGIT);
  if (dm) {
    return { code: Number(dm[1]), source: "egg_code_number", confidence: "medium" };
  }
  return { code: null, source: "unknown", confidence: "low" };
}

export function isShellEgg(product) {
  // Exclude products outside the cage-free shell-egg debate:
  //   - liquid egg / egg whites (claras): processed product, not shell eggs
  //   - quail (codorniz / codorniu): different species, separate market
  //   - cooked eggs (huevos cocidos / ous cuits): housing-system disclosure
  //     not standard on cooked-and-peeled hard-boiled packs even though they
  //     come from laying hens; treated as out of scope for the listing audit.
  const n = (product.name || "").toLowerCase();
  if (/\bclara[s]?\s+(?:de\s+)?huevo|\bclara[s]?\s+l[ií]quida|\bclaras? d'?ou|\bliquid egg/.test(n)) return false;
  if (/codorniz|codorniu|quail/.test(n)) return false;
  if (/\bcocidos?\b|\bcocido\b|\bcuits?\b|\bcuit\b|hard[\s-]?boiled/.test(n)) return false;
  // Latvian exclusions: paipalu (quail), olu baltums/dzeltenums (egg white/yolk),
  // šķidrās olas / olu masa (liquid egg / egg mass), vārītas (boiled).
  if (/paipal/.test(n)) return false;
  if (/olu baltum|olu dzeltenum|[sš][kķ]idr[aā]s? ola|olu mas/.test(n)) return false;
  if (/v[aā]r[iī]t/.test(n)) return false;
  return true;
}

export function codeLabel(code) { return code === null ? "unknown" : CODE_LABEL[code]; }
export function isCageFree(code) { return code === 0 || code === 1 || code === 2; }

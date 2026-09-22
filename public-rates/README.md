# Public Swiss mortgage rates

MIT-licensed, dependency-free Python adapters for **exact lender-published fixed mortgage rates**. These are public rate observations, not personalised or binding offers. They complement the applicant-based quote contract; they must not be inserted into that contract as approved quotes.

## Run

Python 3.10 or newer:

```sh
python3 public-rates/rates.py --output /tmp/mortgages.json
python3 public-rates/rates.py --provider postfinance --provider viac --term 5
python3 -m unittest discover -s public-rates/tests -v
```

The default fetches all providers directly over HTTPS with four workers, a 25-second network timeout and a 4 MiB response limit. No login, API keys, browser, applicant details, partner relationship or paid service is required. Network or parsing failure produces `unavailable` with zero rates for that provider. A partial run writes its successful results but exits **2**, so automation can detect incomplete coverage. There is no last-known-rate fallback. The output file is replaced atomically.

Import `rates.py` to call `providers()`, `fetch(provider)`, `collect(providers)` or `available_rates(document, now, term)`. Provider selection is from the maintained registry, never an arbitrary caller-supplied URL.

## What the output means

- `annualRatePercent` is a decimal string in percentage points, copied from the source with decimal comma normalised. Precision is preserved. It is **not APR**.
- `sourceEvidence` preserves the matching term/rate text. `publishedRateText` preserves the source decimal spelling. No interpolation, discount subtraction, repayments or inferred rates occur.
- `qualifier: from` preserves an advertised minimum. All records have `binding: false`, `personalised: false`, `derived: false`.
- `retrievedAt` is the actual fetch time. `sourcePublishedDateText` is separate and null when the source does not publish a recognised date. Do not relabel retrieval as a lender update.
- `expiresAt` imposes a 24-hour **local freshness policy**, not a lender rate guarantee. A provider's explicit validity date can shorten this. Consumers must use `available_rates` or enforce equivalent expiry; a saved JSON file does not update itself.
- `conditions` is a reviewed summary, **not a complete eligibility engine**. `conditionsReviewedOn` and `conditionsComplete: false` make this explicit; link the source for full current rules. No eligibility assessment occurs.
- Brands and contracting lenders are not necessarily distinct. Known VIAC/WIR and Swissquote/LUKB relationships are identified; do not advertise the brand count as independent lenders.

Run at most hourly for a comparison deployment and show the retrieval time. No background job or production website activation is installed by this module. Respect source access requirements; this implementation does not bypass blocks. The MIT code licence does not license lender logos or third-party content or imply lender endorsement.

## Verified coverage

Live direct fetch on 22 September 2026: **18 provider brands, 219 product/term entries**. See [verification.json](verification.json) for per-provider counts and response hashes. This is a historical implementation check, never a current-rate feed. Fixtures contain deliberately synthetic `7.123` rates and are not offers.

| Provider | Entries | Included products |
|---|---:|---|
| Bank Cler | 35 | Fixed, Supercard and sustainability tables |
| Bank BSU | 9 | Main fixed-rate table |
| VIAC / Bank WIR | 2 | Fixed 5 and 10 years |
| Hypomat / GLKB | 19 | Fixed 2–20 years, from rates |
| PostFinance | 14 | Fixed 2–15 years, from rates |
| Migros Bank | 18 | Standard and published online preferential table |
| Valiant | 9 | Fixed 2–10 years |
| Luzerner Kantonalbank | 9 | Fixed 2–10 years |
| Swissquote | 9 | Published fixed from rates |
| BPS (SUISSE) | 10 | Fixed 1–10 years |
| Hypothekarbank Lenzburg | 9 | Fixed 2–10 years, including published 10-year special rate |
| AEK BANK 1826 | 10 | First mortgages, 1–10 years |
| acrevis | 9 | Fixed 2–10 years |
| BVK | 11 | Fixed 2–12 years, explicit expiry respected |
| Aargauische Pensionskasse | 14 | Fixed 2–15 years |
| Crédit Agricole next bank | 4 | Swiss-property Ecoprêt from rates only |
| Pensionskasse Stadt Luzern | 14 | Fixed 2–15 years |
| Zürcher Kantonalbank | 14 | Fixed 2–15 years |

Every source URL and scoped extraction rule is in [providers.json](providers.json). Each adapter checks the expected term set, including duplicates, before emitting any provider rates. Multi-column Migros/BPS/CA headings are checked to detect layout changes. A changed layout or term range requires a reviewed adapter update; matches are never accepted just to fill gaps.

## Deliberate exclusions

SARON margins are not all-in mortgage rates; this first module focuses on fixed rates. Migros ECO rates for terms longer than five years have a time-limited discount, so the ECO table is not represented as a flat full-term rate. BSU's separate limited campaign needs its own complete campaign adapter. PKSL's advertised ECO discount is not subtracted. Cler's securities-account discount is not calculated. CA's French-property CHF/EUR columns are excluded.

Swiss Life returned HTTP 403 during direct verification; no access workaround was attempted. The inspected ZugerKB page did not return a rate table; no cached search values were substituted. Neither is counted as a working adapter.

Future contributions should add a first-party source, bounded product-specific parser, dates/expiry semantics, conditions and synthetic regression fixtures. Test missing rows, duplicate terms, altered columns, expired data and fetch errors. Manually reconcile the complete initial result with the provider page; tests alone cannot certify a lender's offer.

# Swiss public consumer-credit providers

MIT-licensed adapter code (repository LICENSE). Python 3.10+, no third-party dependencies. These adapters retrieve **published pricing**, not personal credit offers. No authentication, application submission, personal data or lender contact is used.

```sh
python3 public-credit/credit.py
python3 public-credit/credit.py --provider cashgate --output /tmp/credit.json
python3 -m unittest discover -s provider-integrations/public-credit -p 'test_*.py'
```

Run these commands from the provider-integrations repository root.

Library: import `collect`, `fetch`, `parse`, `providers`, `available_rates` from `credit.py`. `collect()` always performs fresh HTTP reads, emits no cached fallback, and records individual source failures. CLI exits 1 on any failed source, while preserving successful records. A missing/changed rate anchor or conflicting range fails closed. Prices are decimal strings copied from source (comma normalized to decimal point); no payment or interest arithmetic occurs.

## Coverage

| Brand / provider | Public data | Records |
|---|---|---:|
| [Migros Bank](https://www.migrosbank.ch/de/privatpersonen/kredite/privatkredit.html) | Effective annual interest range for online personal loans | 1 |
| [BANK-now](https://www.bank-now.ch/de) | Effective annual interest range | 1 |
| [bob Finance](https://www.bob.ch/de/privatkredit/) | Effective annual interest range | 1 |
| [LEND](https://lend.ch/de/darlehen) | Effective annual interest range; crowdlending platform | 1 |
| [Cembra](https://www.cembra.ch/de/kredite/barkredit/) | Effective annual interest range | 1 |
| [cashgate](https://www.cashgate.ch/de) | Effective annual interest range and 9 explicitly published cohort/term prices | 10 |

Total: **6 brands, 15 records**, not 15 competing offers. Cashgate is a Cembra brand. The cashgate range overlaps its cohort table. Never rank a range minimum as if it were the user's approved interest rate. The cashgate published matrix uses `≤48`, `60`, and `≥72` months: do not interpolate unlisted terms. It does not state a rate for every income/residence combination. An eligibility cohort is not a creditworthiness assessment. Approval remains with the lender.

## Provenance and freshness

Every observation has source URL, retrieval UTC time, SHA-256 of the fetched page, literal rate evidence and a 24-hour freshness TTL. Provider effective dates are `null` when the source does not establish one; the retrieval date is not a publication date. `verified-snapshot.json` is a historical verification artifact, **never live inventory**. Use `available_rates(document, now)` before displaying stored observations. It rejects malformed, future-dated and older-than-24-hour records, respects shorter record TTLs, and excludes providers reported as failed. Pass an explicit timezone-aware datetime or ISO timestamp. Fetch again and show unavailable if fresh retrieval fails. CLI `--output` uses an atomic same-directory replacement, so readers never see a partially written JSON document. The library deliberately has no fallback to that snapshot. Pages may be cached by publishers/CDNs despite a successful read; this is periodically fetched public pricing, not a streaming quote feed.

Current checks: all 6 official URLs successfully fetched and parsed in the timestamped snapshot. Tests cover range semantics, conflicting numbers, missing pages, hidden script content and cohort table drift. Source texts may change; monitor failures and review provider changes.

## Deliberate exclusions

No generalized leasing or credit-card quote engine is included. A car-leasing example depends on the named car, cash price, initial payment, mileage, term and residual value; copying its headline APR into a generic offer would lose material conditions. No derived loan repayments, hypothetical lending decisions, scraped authenticated quotes, or third-party comparison prices are emitted. Cembra's application URL and marketing page showed differing search-index snippets during research, so this adapter uses only its directly fetched official Barkredit page, never snippets.

Public access does not establish an open-data licence. The **code** is open source; lender text, trademarks and pricing datasets retain their own rights. No open-data licence was verified for these sources. Maintain attribution and check permitted reuse before commercial redistribution at scale. No affiliations, commissions or referral tracking are added.

## Cashgate matrix interpretation

Rechecked the live desktop and mobile HTML matrix on 2026-09-22. Its income heading is only “Monatliches Einkommen”: it does **not** identify gross or net income. Accordingly every cohort emits `income_basis: "not specified by source"`. The ≥ CHF 4,500 rows list Swiss passports and C permits only, split by homeownership; the < CHF 4,500 row lists Swiss passports, C permits and B permits and displays a dash for homeownership. B-permit holders earning ≥ CHF 4,500 have no explicit matrix cell: do not assign them the lower-income price, infer ineligibility, or extrapolate. No borrower-to-cohort quote selection is implemented.

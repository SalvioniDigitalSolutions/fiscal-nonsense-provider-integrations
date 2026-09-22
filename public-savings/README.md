# Swiss public savings and pension cash-rate providers

Five independent public-page adapters, using Python 3 standard library only. Run from this directory:

```sh
python3 providers.py --output latest.json
python3 providers.py --provider zkb --provider hbl
python3 -m unittest -v
```

Import `providers.fetch("hbl")` for one bank, or `parse(provider_id, html)` to test an independently downloaded page. The CLI returns a nonzero exit code if any source fails, while preserving successful sources in its output. No credentials, customer information, private endpoints or browser sessions are needed.

## Coverage

| Source | Product schedules | Published percentage occurrences |
|---|---:|---:|
| Hypothekarbank Lenzburg | 7 | 10 |
| Zürcher Kantonalbank | 7 | 10 |
| Bank BSU | 7 | 13 |
| Valiant | 8 | 13 |
| Bank Cler | 6 | 9 |
| Total | 35 | 55 |

These are **35 product rate schedules, not 55 separate offers**. Categories include savings, rental-deposit savings, cash pillar 3a and cash vested-benefit accounts. Valiant's EUR/USD accounts and Cler's EUR account are explicitly currency labelled. All others are CHF.

## Exactness and interpretation

`published_rates[].percent` is a string in percentage units, transcribed from the current page. Decimal comma and whitespace are normalized; no rates are added, subtracted, annualized or inferred. `published_text`, `evidence_text` and occurrence offsets preserve the evidence. A multi-value schedule preserves provider wording for balance thresholds and conditional rates; **do not choose the largest value or treat all values as universally applicable**. Cler's 3a schedule includes base/package rates and corresponding page footnotes. Qualification, age, withdrawal rules and fees may require the linked product terms; this is not a complete suitability or account-cost calculator.

Investment returns, investment management fees, forward projections, calculated SNB-linked interest, and negotiated rates are excluded. BSU eco schedules require a deduction and are excluded. Promotional BSU Spezial and Cler bonus accounts are excluded pending a complete promotion expiry/eligibility adapter. Valiant Lila tier rules are excluded pending complete tier qualification. WIR has dynamic placeholder rates and is not implemented. No fabricated default or historical rate is returned on a failure.

## Freshness and reliability

Each run directly retrieves the official HTTPS source using `Cache-Control: no-cache`; no search-engine cached rates or fallback snapshots are used. Each successful source is timestamped and each product includes source URL and SHA-256 hash. `latest.json` is a **dated verification artifact**, never inherently a live feed. Refresh before display and use `is_fresh(record)` to reject artifacts older than 24 hours, future timestamps, naive timestamps and failed results. `--output` atomically replaces the destination only after writing complete JSON. Fetch time is not the lender's effective rate date. A lender may still publish an old effective date for an unchanged current rate. Published date labels are supplementary; ZKB's product evidence also retains its specific update date.

Adapters fail closed for missing blocks, changed percentage counts, or ambiguous repeated blocks. The CLI reports partial failures explicitly. Manual review is required after source layout/meaning changes. HTML scraping is not a guaranteed bank API, and a successful extraction does not guarantee that the rate is available to a specific applicant. Preserve source terms and attribution and check reuse/crawl terms before operating at scale.

## Licensing

Adapter code and tests are MIT licensed (see LICENSE). Bank content, branding, rates and source excerpts remain third-party content; this code license does not grant an open-data licence to bank content or imply bank endorsement. Public visibility alone is not an open-data licence.

# Swiss public insurance tariffs

A standard-library Python adapter for **exact published Swiss basic-health premiums** from the Federal Office of Public Health (BAG/FOPH). It copies the premium field unchanged. It does not reverse-engineer insurer calculators, calculate discounts, collect identities, submit applications, or promise eligibility.

## Verified coverage

Network verification on **22 September 2026** imported **217,472 tariff rows across 34 insurers and all 26 cantons**. These are combinations of insurer, model, canton/region, age class/subgroup, deductible and accident coverage—not 217,472 distinct insurance products. The archive also has 164 special-territory rows (ZE/ZR); `list` excludes those, leaving **217,308 ordinary-canton rows**. The verification receipt is in `verification.json`; its timestamp is evidence of that run, not a permanent live claim.

The current unversioned BAG premium CSV was header-only when checked during the 2027 data rollover. The provider therefore uses the official **2026 archive**, validates every row's coverage year and refuses to serve it outside 2026. An annual archive can contain tariffs still valid today. Future years require a successful fresh fetch of that year's official archive; if unavailable, this adapter fails closed until the source path is reviewed. It never silently substitutes another year.

## Run from the repository root

```sh
python3 public-insurance/insurance.py refresh
python3 public-insurance/insurance.py list --canton AG --region 'PR-REG CH0' --age AKL-ERW --accident MIT-UNF --deductible FRA-300 --limit 20
python3 -m unittest discover -s public-insurance -v
```

`refresh` performs a public HTTPS download, validates and atomically builds `public-insurance/data/premiums.sqlite`. No API key is required. `--db /path/catalogue.sqlite` before the subcommand changes its location. `--archive /path/official.zip` supports local import for inspection, but marks it **unverified** and cannot be served by `list` as live data.

`list` is a catalogue lookup, not a personalized quotation engine. No matching row means no offer; there is no interpolation or invented fallback. Prices are monthly CHF amounts exactly as published (strings preserve precision). Every result retains the original source row. Results are deterministic, with pagination by limit only; a limit does not imply market completeness or cheapest ranking. `totalMatchingRows` identifies truncation.

Filters use official source codes:

- `--insurer`: BAG number, without leading zeros, e.g. `8` for CSS.
- `--canton`: canton abbreviation.
- `--region`: complete official premium-region code such as `PR-REG CH0`.
- `--age`: `AKL-KIN`, `AKL-JUG` or `AKL-ERW`.
- `--accident`: `MIT-UNF` or `OHN-UNF`.
- `--deductible`: e.g. `FRA-300`.
- `--tariff` and `--subgroup`: exact source codes, when required.

Do not infer a municipality's premium region from postcode alone. Do not interpret a child subgroup code as an age range without reading the tariff definitions. The adapter includes the insurer tariff definitions, model catchment rows and raw insurer activity table with its output. Municipal catchment, doctor/model access and subgroup requirements still need checking before claiming an applicant qualifies. `eligibilityVerified` and `personalizedQuote` are always false.

## Consumer freshness contract

The database expires 24 hours after a network refresh. `catalogue()` calls `validate_metadata()` to reject expired, future-dated, invalid-expiry, unverified and wrong-year data. If an application saves a JSON response, it **must call `validate_metadata(response['metadata'])` again at serving time**; a previously successful CLI exit is not a freshness guarantee. Refresh errors must not cause the application to relabel older snapshots as current. Import failures leave the previous cache intact, but it remains subject to its original expiry.

Library entry points in `insurance.py`: `download`, `source_url`, `import_archive`, `catalogue`, `validate_metadata`, `SourceChanged`. Import with Python's `importlib` or put this directory on the module path.

## Sources and rights

- [Official Priminfo download index](https://www.priminfo.admin.ch/de/downloads/aktuell)
- [BAG dataset and resource catalogue](https://opendata.swiss/de/dataset/health-insurance-premiums)
- [Official 2026 archive resource](https://opendata.swiss/de/dataset/health-insurance-premiums/resource/2dc39d7d-6c55-4a57-82f9-60237467127e)
- [Official insurer directory, January 2026](https://www.priminfo.admin.ch/downloads/zugelassene-krankenversicherer-2026-01-01.xlsx)

Provider display names in `insurers-2026.json` are transcribed from the directory index; only insurers represented in actual premium rows count toward coverage. The directory contains other authorized insurers without rows in this particular dataset.

Repository licensing applies to adapter code. The dataset metadata currently declares no license; do not interpret our code license as a grant over third-party source data. Full source archives and the local database are not included in git. Attribution, source URL and SHA-256 are recorded with every import.

## Other insurance categories researched

| Category / source | Result |
| --- | --- |
| [Allianz Travel annual insurance](https://www.allianz-travel.ch/de_CH/reiseversicherungen/jahresreiseversicherung.html) | Public page contains 15 explicit annual prices across three plans and individual/family age bands. Direct automated HTTP fetch returned 403 here, so it is a documented candidate, **not counted as a working live adapter**. Family pricing also depends on ages in the household. |
| [TCS ETI travel cover](https://www.tcs.ch/de/produkte/pannenhilfe-reiseschutz/reiseschutz/) | Membership and promotional/configuration conditions need a reviewed mapping; not implemented or counted. |
| [Simpego liability insurance](https://www.simpego.ch/de/haftpflichtversicherung) | Public product page inspected shows coverage amounts and deductibles, not an implementable premium tariff table. Those amounts must never be mistaken for premiums. |
| Motor, home contents, supplemental health and life insurance | No verified public tariff adapter delivered in this folder; no prices fabricated. This is not a claim that no provider publishes any usable price. |

The adapter is independently maintained, not an official BAG service or insurer endorsement.

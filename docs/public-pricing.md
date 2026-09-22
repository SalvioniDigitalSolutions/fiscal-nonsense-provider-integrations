# Exact publicly published Swiss pricing

These open-source adapters provide a second integration route alongside hosted personalised quote APIs. They fetch publicly accessible provider pages or the official BAG basic-health tariff archive. No applicant data, authentication, paid API subscription or quote submission is needed.

**Published pricing is not a guaranteed personal quote.** Each category preserves its actual semantics: an exact mortgage rate for a term, a loan rate range or conditional matrix, a savings interest schedule, or an exact insurance tariff row. Never flatten these into interchangeable offers or present a range minimum as an approved rate.

## Implemented coverage

Verified by direct network retrieval on **22 September 2026**:

| Category | Public-source coverage | Result |
|---|---|---|
| [Mortgages](../public-rates/README.md) | 18 provider brands | 219 exact fixed product/term rates, including explicitly printed preferential tables |
| [Consumer credit](../public-credit/README.md) | 6 provider brands | 6 published annual-rate ranges plus 9 cashgate conditional table entries |
| [Savings and pension cash accounts](../public-savings/README.md) | 5 banks | 35 product schedules, retaining rate tiers/conditions; includes pillar 3a and vested benefits |
| [Basic health insurance](../public-insurance/README.md) | Official BAG tariffs for 34 insurers | 217,308 ordinary-canton 2026 premium rows, covering all 26 cantons (217,472 archive rows including special territories) |

Counts describe coverage of this implementation check, not guaranteed future availability. They are not additive counts of independent financial institutions: brands and lender groups overlap. The health figure counts tariff combinations, not insurers or immediately eligible personal offers. The loan-range and conditional-table counts overlap for cashgate. Savings schedules can contain several balance tiers.

## Run from the repository root

Python 3.10+; all four modules use the standard library only.

```sh
# Fresh public mortgage and loan observations
python3 public-rates/rates.py --output /tmp/mortgages.json
python3 public-credit/credit.py --output /tmp/credit.json

# Fresh savings, cash 3a and vested-benefit schedules
python3 public-savings/providers.py --output /tmp/savings.json

# Download and validate the official current-year health archive, then select rows
python3 public-insurance/insurance.py refresh
python3 public-insurance/insurance.py list --canton ZH --age AKL-ERW --deductible FRA-2500 --limit 20

# Offline regression tests for every public category
python3 scripts/test-public-pricing.py
```

Read the health module's documented source codes before filtering; the API returns source dimensions and restriction tables, and does not resolve municipal catchment or confirm eligibility. Its locally cached SQLite catalogue must be refreshed; tariff year and retrieval freshness are both validated before results can be served.

Category-specific schemas are documented in each module. They intentionally do not conform to the personalised v0.1 quote response: its repayment/coverage/eligibility fields cannot be filled honestly from a public rate table. Integrators can import each Python module and retain its typed payload under a category key. Do not convert a tariff row into an eligibility-confirmed offer or manufacture missing APR, fees, repayments or investment returns.

## Freshness and operations

Mortgage, credit and savings adapters fetch sources directly on each run; failures are explicit and do not fall back to bundled verification data. Consumers must use the documented freshness helpers when serving saved results. A source page can remain unchanged for months; retrieval time is distinct from a lender-published effective date. Local 24-hour limits are freshness policies, never guarantees of a lender's rate.

The insurance module downloads the official year-specific archive because the undated current file was header-only during the next-year rollover. It requires the current policy year and a network-verified, unexpired catalogue. It keeps every price as a source decimal string, along with tariff, region, age, accident, deductible, subgroup and restrictions. It calculates no premium or rebate.

No service, website publication or recurring refresh is installed by these libraries. Historical `verification.json`, `verified-snapshot.json` and `latest.json` files are implementation evidence and must never be served as a live feed. Production integration must preserve source links, dates, conditions, errors and category distinctions, and refresh before expiry.

## Sources that do not yet support a working adapter

- Swiss Life mortgage page blocked direct retrieval; no block bypass or cached-search substitute.
- The inspected ZugerKB mortgage page did not expose a usable table.
- SARON margins are not full mortgage rates; this mortgage module is fixed-rate only.
- Individual car/property/supplementary-health/life insurance and investment pension projections need additional tariff dimensions or a provider quote API. Basic-health tariffs do not generalise to these products.
- Leasing examples are tied to a vehicle, down payment, residual, mileage and term; they are not generic personal-loan quotes.

Each category README records further limitations and candidates. Missing coverage means no supported public adapter was verified in this pass, not that no public information exists anywhere.

## Contributing and licensing

Add maintained first-party sources with product-scoped extraction, exact decimal output, provenance, conditions and synthetic regression fixtures. Test missing/duplicate rows, reordered rate columns, fetch failure and expiry. Reconcile every initial value against a fresh provider response. No discounts, rates or missing prices may be derived to increase coverage.

Code is MIT licensed under the repository [LICENSE](../LICENSE). That licence does not relicense source data, logos or lender text, and does not imply a provider relationship. These adapters add no affiliate tracking, commissions or paid referrals.

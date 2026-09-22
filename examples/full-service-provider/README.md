# Nonsense Cover & Credit — fictional full-service example

**No company, API, offer, licence or partnership represented here exists.** All 41 catalogue entries and prices are synthetic, never consumer results. `.example` addresses are non-production placeholders. Fixed fixture time: 2026-09-22T10:05:00Z.

This is one fictional group with insurance, lending and retirement divisions, illustrating a multi-product submission. A real submission must identify the actual insurer/underwriter, lender and any intermediary for every product; a brand is not automatically authorised to underwrite or lend. The CH/CHF market is illustrative, not an assertion that all product structures are offered or permitted there.

Every category in `taxonomy.json` has a product entry and an offline success fixture. `no_quote.json` and `unavailable.json` show explicit failures. Fixture prices demonstrate serialization only: they are not actuarial calculations, real tariffs or suitable reference prices. No APR or repayment amount is fabricated for credit fixtures.

## Structured form objects

Each product has a paired request/response fixture and a strict schema in `input-schemas/`. Requests contain reusable applicant/risk/coverage/credit/pension objects, plus typed provider-specific fields. This fictional group declares its required fields and conditional branches; a real provider must replace them with its verified questionnaire and mappings. The reserved postal code and names identify synthetic data, not real customers.

| Product group | Input and output differences to specify |
|---|---|
| Motor | Vehicle, drivers, use, territory, claims, coverage and excesses |
| Home / property | Location, occupancy, building/contents values, per-risk limits |
| Health / dental / care | Region, age, plan, deductible, co-insurance, annual caps and eligibility; minimise sensitive information |
| Life / disability | Benefit amount and duration, term, eligibility, waiting periods, underwriting route |
| Travel / pet / legal / liability | Covered people/animals/activities, territory, duration, limits and exclusions |
| Commercial / cyber / marine / specialty | Business activity, exposures and requested limits; specialist schema may be necessary |
| Mortgage / secured / bridging | Loan, collateral, LTV, duration, repayment type, rate periods, fees, balloon balance and local APR definition |
| Personal / student / business / vehicle | Principal, term, purpose, eligibility, payment schedule and total payable |
| Cards / overdrafts / lines | Credit limit, usage assumptions, promotional periods, variable rates, minimum payment and charges |
| BNPL / leasing | Cash price, deposit, instalments, ownership, residual/buyout amount, fees and late-payment rules |

The structured family objects are an initial exchange envelope. Complex products require a reviewed extension for structured category-specific terms before automated comparison or price ranking. Passing fixture checks does not mean a product is consumer-ready.

## Retirement and pension provision (previdenza)

Seven further examples cover occupational/private pensions, Swiss pillar 3a/3b, annuities, transfers/vested benefits and specialist provision. They show synthetic contributions, fees and explicitly illustrative accumulation projections. Real inputs may include scheme membership, age/retirement horizon, contribution or transfer amount and payout preferences. Provider-specific rules must determine eligibility, limits and benefit illustrations. No single pension formula applies across markets.

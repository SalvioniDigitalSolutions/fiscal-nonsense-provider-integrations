# Structured quote contract · draft v0.1

The authoritative shapes are in `schemas/contract.schema.json`; each provider supplies a strict product-specific schema for `input.providerData`. This is a proposal and offline validation kit. There is no production gateway, active insurer or credential service yet.

## 1. Shared objects

A request contains `schemaVersion`, `requestId`, `providerId`, `productId`, `country`, `currency`, `applicant` and `input`. Money values are decimal strings with two fractional digits in the request/quote currency; percentages are decimal strings in percentage points (e.g. `6.00` means 6%, not 0.06). Date-only fields use YYYY-MM-DD; timestamps are UTC ISO with a Z suffix. A correlation ID must not contain a customer identifier.

`applicant` contains individual/organisation kind, residency country, postal code and age when relevant. Never infer nationality, health, credit standing or eligibility from location alone. No universal identity-document upload or payment collection is part of this contract.

## 2. Provider and product objects

One manifest can declare many products across insurance, credit and retirement families. Each product identifies its category, markets/currencies, contracting entity and role, core input schema, providerData schema, risk kind where applicable, pricing model and fixture-only implementation status.

The 41-category taxonomy is extensible. It does not prove that a product exists in each country, that every legal product type is covered, or that a multi-brand group has one underwriting entity. Propose missing categories with their own schema and fixtures.

## 3. Complete provider-required inputs

The core object provides reusable types. `input.providerData` is **not an unvalidated catch-all**: its schema is supplied in `input-schemas/<product>.schema.json`, compiled before use, and must reject unknown properties. Required properties and JSON Schema `if` / `then` / `else`, `oneOf` and array constraints express the exact questionnaire. All declared requirements are validated before dispatch. Schemas do not load remote references.

For example, a car quote's common objects identify cover, vehicle and drivers. The provider extension supplies make/model/variant, registration details, use, licence and loss history. Declaring previous claims makes dated claims with amounts mandatory. Business use requires the business-use object. The mortgage example similarly requires an existing-loan object for refinancing and a co-borrower object for joint applications.

**No fixed global schema can anticipate every insurer's underwriting rules.** Providers must verify every necessary data point, permitted omission, conditional branch, derived value, unit, code list and jurisdictional requirement. Never substitute an undocumented default for an unanswered question. The example's fictional requirements are not approved production questionnaires.

For real submissions:

1. Supply an authoritative field specification and schema, including property titles/descriptions and safe formats/bounds/enumerations.
2. Give test cases for ordinary eligibility, every conditional branch, omitted required data, invalid values and ineligibility.
3. Document cross-field rules (dates, age, co-insured totals, LTV, payment capacity, limits) that need code beyond JSON Schema. Provide reviewed validators before activation.
4. Reconcile duplicated provider-specific and core fields through a documented mapping; reject contradictions. The example data is illustrative and does not replace this provider-specific mapping.
5. Label high-sensitivity inputs and justify necessity, processing roles and retention before exposing them in a visitor form. A schema does not itself authorise collecting health or credit data.

## 4. Insurance input and output

The core input declares policy start, term, payment frequency, a typed risk (vehicle, property, person, travel, pet, business, household liability or specialist exposure) and requested coverages. Product-specific fields complete the questionnaire.

The output has premium base, taxes, mandatory fees, total and payment period; cover dates; structured coverage limits (null for no monetary cap in this field), deductible basis, coinsurance/caps and waiting periods; exclusions, renewal and cancellation notice. The validator checks premium arithmetic and matching requested terms. All numbers in the example are fictional.

Products with aggregate deductibles, benefit-specific limits, indexed benefits or other structures beyond these fields need the relevant structured extension. A simple fixed deductible is not an adequate health model. Do not rank dissimilar coverage solely by premium or annualise monthly premiums without the actual instalment terms.

## 5. Credit input and output

The input distinguishes installment and revolving facilities, amount, term, repayment model, income/debt, optional collateral/deposit/residual and usage assumptions. Detailed borrower, employment, financial, joint-applicant, property/vehicle/study/business and refinance information lives in the per-product schema.

Installment outputs contain principal, nominal annual rate, fixed/variable basis, APR with its jurisdiction/definition (or explicit unavailability), fees, complete dated principal/interest/payment/balance schedule, total payable, total interest and final balance. `totalPayable` is the sum of scheduled payments; **a nonzero final balance is separate** and must be displayed as still owed. No fee can be silently omitted; the final integration must reconcile all fees and cashflows. The examples have no credit fees. Nominal rate is not APR.

Revolving outputs have minimum-payment rules and a usage illustration. They do not pretend an open credit line has a guaranteed fixed repayment term. Promotional balances, daily accrual, leasing, student deferment and other complex structures require reviewed extensions.

A null APR is valid for an offline proposal, not evidence of a compliant live consumer offer. Country/product disclosures must be reviewed before launch.

## 6. Retirement provision / previdenza

Inputs contain age/horizon, initial capital, contributions, payout preference, employment, scheme and transfer details. Each scheme adds its exact membership, salary, tax-region, insured benefits, beneficiary, guarantees and transfer information.

Outputs separate contributions, fees, guarantees, projections, access restrictions and risks. Every projection declares `illustrative: true`, horizon, assumed gross/net return, fees, contribution timing, inflation/tax treatment and calculation methodology. Never present assumed returns as guaranteed interest. Annuity benefit pricing and occupational pension accrual need their own reviewed methods; accumulation projections cannot substitute for them.

No statutory contribution cap, tax advantage or legal entitlement is invented by these fixtures.

## 7. Response envelope and failures

Responses echo request and provider IDs, with `mode: sandbox|live` and `status: quoted|no_quote|unavailable`. Non-quoted responses contain an empty quotes array and a non-sensitive explanation. Never treat zero as an unavailable quote.

Each quote has provider product, country/currency, indicative/personalized price kind, assumptions, UTC issue/expiry and reviewed HTTPS quote/terms links. The validator rejects expired/future, mixed-family, mismatched and wrong-mode results. Personalised does not mean a bound policy or approved loan.

Offline fixtures use 2026-09-22T10:05:00Z as their explicit test clock. Production validation must use actual current time and mode live; test dates must never renew old offers.

## 8. Transport and review

An actual API would receive POST JSON from an approved server-side gateway, with privately provisioned authentication. Existing provider APIs may be mapped rather than rewritten. Agree timeouts, rate limits, retry/idempotency, response limits, secrets, allowed hosts/redirects, support and version changes. This repository performs no live requests and does not implement that gateway.

Before launch, verify provider identity, authorisations, data/display rights, visitor disclosures and data processing. Schemas/code from PRs require security review. The production system must not compile arbitrary public schemas on demand or fetch arbitrary manifest URLs. No PR has production secrets or automatic activation.

Quotes are obtained for current inputs at search time. Weekly source checks are separate monitoring. Never silently trigger applications, purchases, credit searches, callbacks or marketing. See review-and-launch.md.

# Fiscal Nonsense · Provider integrations

**Bring your prices. We will check the maths.**

An open contribution programme for insurers, lenders, pension providers and pricing-platform operators who want their quotes to appear on [Fiscal Nonsense](https://fiscalnonsense.com/providers/).

## Public Swiss pricing adapters

Working open-source adapters now retrieve exact public Swiss mortgage rates, consumer-loan pricing, savings/pension cash rates and official basic-health premiums. See **[public pricing documentation](docs/public-pricing.md)** for coverage, commands and limitations. These use first-party public sources and require no applicant information. They are separate from the personalised quote gateway and are not activated there.

## Status: accepting integration proposals

This repository defines a **draft v0.1 interface** and an offline test kit. The production gateway is hosted at [api.fiscalnonsense.com](https://api.fiscalnonsense.com/), with its forms connected to the website provider directory. There are no active insurers or automatic activations from this repository. All proposal example prices are fictional; the public-pricing modules fetch real published values and label historical verification artifacts separately. Passing tests or merging a pull request does not enable an integration on the website.

We welcome proposals for Switzerland (CH), the United States (US), the United Kingdom (GB), Germany (DE) and Italy (IT). The taxonomy covers personal and business insurance, mortgages and other consumer/business credit. It is extensible: propose missing product types instead of forcing them into an unrelated category. Each product needs country-specific inputs and terms before activation.

## Are you an insurer?

1. Read [the integration specification](docs/integration.md) and [contribution guide](CONTRIBUTING.md).
2. Fork this repository. Copy `examples/full-service-provider/` to `providers/your-provider-id/`.
3. Describe your legal entity, markets, coverage, requested inputs, API and contact. Provide **synthetic** request/response fixtures for success, no quote and unavailability.
4. Run `npm test` and `npm run validate` using Node.js 22 or later, after `npm ci --ignore-scripts`. No accounts, credentials or live requests are needed for these checks.
5. [Open a pull request](https://github.com/SalvioniDigitalSolutions/fiscal-nonsense-provider-integrations/compare) with the provider template. Our team reviews identity, data permissions, matching coverage and pricing behaviour before any launch.

For commercial questions or private integration details, email **info@fiscalnonsense.com**. Arrange a secure credential exchange with us; do not email API secrets or place them in issues, PRs, examples or Git history.

## Structured quote objects

Every request identifies provider, product, country and currency, with a common applicant object and one typed `insurance`, `credit` or `retirement` input. Each product also supplies a **strict provider-specific JSON Schema** for its full questionnaire. Missing required data, unknown fields and unmet conditional requirements are rejected before a quote request.

The fictional full-service example contains **41 product input schemas and 43 success/error fixtures**, including nested data for vehicles/drivers, property, health, claims, businesses, employment, debt, collateral and pension schemes. Follow-up requirements demonstrate claims, joint borrowing, refinancing, business vehicle use and medical conditions.

These examples are comprehensive starting points, **not an assertion that every future provider requirement is already known**. Real providers must supply their exact required data, conditional rules and validation cases. A working integration cannot be approved on the basis of a generic fixture alone.

Outputs distinguish premium/tax/fee components, coverage/excesses, nominal rates versus APR, repayment schedules, revolving-credit rules, pension contributions, charges, guarantees and non-guaranteed projections. Sandbox fixtures never appear in the consumer directory.

## Integration routes

- **Your hosted quote API:** return prices from your own pricing engine using the proposed contract or document your existing API for a mapping review.
- **Your embeddable calculator:** propose documented, permitted embedding. State branding, domain restrictions, consent flow and whether results can be shown outside the embed. No promise that we can extract or restyle its prices.
- **Your published tariff dataset:** supply an authoritative source, reuse terms, effective dates, complete rating dimensions and eligibility rules. A tariff implementation requires separate review and reconciliation against your official calculator.

An existing API does not have to match our draft exactly. Open an integration proposal first; do not publish proprietary algorithms or licensed data you cannot redistribute.

## Repository map

- `docs/public-pricing.md`: working public-data adapters, coverage and refresh instructions.
- `docs/integration.md`: input/output contract, numerical conventions and operational requirements.
- `schemas/contract.schema.json`: machine-readable structured request and response objects.
- `docs/review-and-launch.md`: review and explicit activation process.
- `examples/full-service-provider/`: fictional provider and offline fixtures.
- `lib/contract.mjs`: envelope validation helpers; no networking or production integration.
- `taxonomy.json`: 41 initial insurance, credit and retirement categories, with four-language labels.
- `.github/ISSUE_TEMPLATE/provider.yml`: integration proposal.

Templates and code are MIT licensed. That license does not grant rights to insurer branding, datasets, quotes or third-party APIs. Production use and commercial arrangements are agreed separately.

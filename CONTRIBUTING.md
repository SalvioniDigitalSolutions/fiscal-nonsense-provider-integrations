# Contributing a provider

Submit public integration documentation and synthetic fixtures only. You must have authority to submit the material and describe the proposed provider relationship accurately.

## Submission contents

Create `providers/<id>/` with:

- `provider.json`: follow the example fields. Keep `status` set to `proposed`; there is no automatic activation flag.
- `input-schemas/<product>.schema.json`: strict JSON Schema 2020-12 defining every provider-required product field and conditional requirement. Add synthetic positive and negative cases for each conditional path.
- `fixtures/<case>.json`: paired synthetic request/response cases, at least one per declared product plus `no_quote` and `unavailable` cases.
- `README.md`: actual public API documentation, eligibility, all required/optional form fields, supported regions, deductible and limit conventions, renewal terms, known exclusions, error mapping, rate limits, versioning and intended commercial relationship. Explain why each requested field is needed.

Use a provider ID containing lowercase letters, digits and hyphens. List a public technical contact, official website and documentation URL. Public endpoint addresses are welcome; API credentials are not.

Run `npm ci --ignore-scripts`, then `npm test` and `npm run validate`. CI checks offline data contracts only. It cannot establish that you represent an insurer, that a premium is correct, that coverage is equivalent or that an integration is authorised.

Changes to executable code and workflows receive separate manual security review. Fork PRs receive no deployment credentials. Do not add live network calls to CI or third-party packages to provider directories. Never copy customer records, real quote references or confidential contracts into GitHub.

## Code and data rights

Contribute only material you are entitled to publish under this repository's MIT license. Third-party data access and the right to display production results must be documented separately. Do not include provider trademarks as reusable assets without permission.

## Help without a developer

Open an integration proposal with your public documentation, or email info@fiscalnonsense.com. We can discuss an existing API, authorised embed or published tariff source without requiring a new pricing engine.

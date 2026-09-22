# From pull request to displayed prices

1. **Proposal:** establish whether an API, authorised embed or published tariff is suitable. Confirm markets and products.
2. **Identity and rights:** independently verify the submitting organisation through its official domain, its role, necessary authorisations and data/display rights. A GitHub account is not proof of insurer identity.
3. **Technical review:** run offline fixtures, manually review code and input mappings, then arrange sandbox access privately. Review any endpoint's ownership and allowed traffic before making requests.
4. **Price reconciliation:** compare provider results against official calculator outputs for agreed synthetic cases. Check currency, annual payment basis, taxes/fees, deductibles, coverage, dates, exclusions and ineligible cases. Keep a private review record without customer data.
5. **Operating agreement:** agree responsibilities, disclosures, commercial terms, ranking treatment, support and failure behaviour. Do not promise whole-market coverage or independent underwriting groups based on a brand count.
6. **Explicit activation:** a maintainer enables the integration in a separately controlled production service only after these gates. Merging this repo or changing a manifest never activates it. No public PR code runs with production secrets.
7. **Monitoring:** suppress expired/invalid results, provide a per-provider kill switch and retest breaking API changes before rollout. Public documentation monitoring may run weekly; personalised quotes are obtained per search.

The [production quote gateway](https://api.fiscalnonsense.com/) is deployed, but there are currently **no active providers** in this programme. This repository opens the door to integrations; it does not itself establish a partnership or regulatory permission.

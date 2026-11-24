# Decision records

Short records of the main design decisions in Solvi: the context, the choice, what it costs, and what was turned down. Solvi is a fictional company, but these are the real choices behind this repo.

The plan they belong to, with current and target state, KPI tree, roadmap, business case and security, is at [unadata.dev/solvi/architecture](https://unadata.dev/solvi/architecture/).

| No. | Decision | Status |
|---|---|---|
| 1 | [Split the data by domain, each with an owner](0001-domains-with-owners.md) | Accepted |
| 2 | [Shared data lives once, in core, read through shortcuts](0002-shared-data-in-core.md) | Accepted |
| 3 | [A quality gate in every domain](0003-quality-gate-in-every-domain.md) | Accepted |
| 4 | [Risk rules are a table owned by quality](0004-risk-rules-as-data.md) | Accepted |
| 5 | [Leading indicators replace days without incident](0005-leading-indicators.md) | Accepted |
| 6 | [One Direct Lake model over the gold tables](0006-one-direct-lake-model.md) | Accepted |
| 7 | [Row-level rules in the semantic model](0007-row-rules-in-the-model.md) | Proposed |
| 8 | [HSE events record a role](0008-roles-not-names.md) | Accepted |
| 9 | [One definition per company KPI, with a drill-down](0009-one-definition-per-kpi.md) | Proposed |

A new decision gets the next number. A decision that is replaced keeps its record, with a line saying which one replaced it.

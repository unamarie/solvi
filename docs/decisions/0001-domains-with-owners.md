# 1. Split the data by domain, each with an owner

Status: accepted, November 2026

## Context

Solvi's data sat in an ERP, a CRM, an old ERP, spreadsheets and on paper. Nobody owned it, so nobody fixed it, and the monthly report was built by hand.

## Decision

Six domains follow how the company works: core, sales, supply, delivery, assets and HSEQ. Each has a named owner, its own workspace and lakehouse, and its own bronze, silver and gold notebooks.

## Consequences

- The people who know the data are responsible for it.
- Access can follow ownership (see 7).
- Six workspaces and 24 shortcuts to run, instead of one of each.

## Considered

- One shared lakehouse and model: quicker to start, but nobody owns it, and one change can break many reports.

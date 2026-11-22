# 7. Row-level rules in the semantic model

Status: proposed, November 2026

## Context

Sellers should see the customers in their own area. Security must not slow the reports down.

## Decision

Define row-level rules in the Solvi semantic model, from a table of users and areas owned by sales. Don't define them in the SQL endpoint.

## Consequences

- Reports stay in Direct Lake.
- Anyone who queries the lakehouse with SQL bypasses these rules, so only the data team gets SQL access.

## Considered

- Rules in the SQL endpoint: one place for every tool, but Direct Lake falls back to DirectQuery.

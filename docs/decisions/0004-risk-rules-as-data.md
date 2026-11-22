# 4. Risk rules are a table owned by quality

Status: accepted, November 2026

## Context

The battery risk factors, their weights and the stop rules will change after every near miss.

## Decision

The rules live in a table in HSEQ: code, text, category, weight and whether the factor stops work. The gold notebook scores every job from that table.

## Consequences

- Quality can tune the model without changing code.
- A wrong weight goes straight into production, so changes to the table are reviewed like code.

## Considered

- Rules in the notebook code: one less table, but only a developer can change them.

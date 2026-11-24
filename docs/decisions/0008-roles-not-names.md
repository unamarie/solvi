# 8. HSE events record a role

Status: accepted, November 2026

## Context

People report more when a report can't be used against them. GDPR asks for no more personal data than the purpose needs.

## Decision

An HSE event records who reported it as a role, such as warehouse or customer, never as a name. Follow-up of a person goes through their manager, outside the platform.

## Consequences

- More near misses and good catches are reported.
- Events per person can't be counted. That is intended.

## Considered

- Names with restricted access: possible, but one leak breaks trust in the reporting.

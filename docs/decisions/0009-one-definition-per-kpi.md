# 9. One definition per company KPI, with a drill-down

Status: proposed, November 2026

## Context

Solvi has a few company KPIs, but sellers, purchasers and product owners each read them their own way. Last quarter on-time delivery had three numbers, depending on who made the report. Nobody could say which jobs, suppliers or sellers moved a KPI.

## Decision

Each company KPI gets one written definition and one owning domain. It is written once, as a measure in the Solvi model, together with the measures it breaks down into. Teams can add their own views, but not their own version of a company KPI.

## Consequences

- One number per KPI, and every number opens down to the jobs behind it.
- Someone has to settle disagreements about a definition. The owning domain decides, after hearing the others.
- Reports with local definitions are renamed or retired.

## Considered

- Keep local versions, with a note on each: no change for anyone, but every meeting starts with which number is right.

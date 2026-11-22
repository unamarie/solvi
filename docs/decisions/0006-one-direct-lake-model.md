# 6. One Direct Lake model over the gold tables

Status: accepted, November 2026

## Context

Three apps, and later Power BI reports, need the same measures.

## Decision

A reporting workspace has a lakehouse with shortcuts to every domain's gold tables, and one Direct Lake semantic model, Solvi, with 20 tables and 38 measures. The Fabric script in `fabric/` builds it.

## Consequences

- One definition of each measure, and no import refresh to schedule.
- Some choices make Direct Lake fall back to slower DirectQuery, such as security rules in the SQL endpoint. Keep them out (see 7).

## Considered

- One import model per app: all DAX features and fast, but copies, refreshes and three versions of every measure.

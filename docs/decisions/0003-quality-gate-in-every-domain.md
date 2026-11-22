# 3. A quality gate in every domain

Status: accepted, November 2026

## Context

Errors are cheapest where they start. A wrong value found in a report has already been used.

## Decision

Each silver notebook checks keys, links to other domains and value ranges. A failed check stops the run, so nothing is published. Every check is logged.

`tools/gatetest.py` feeds core one impossible value and checks that the gate stops it. GitHub runs it on every push.

## Consequences

- Bad data stops with the owner, who can fix it.
- A stop delays everything downstream, so owners need to act within two working days.

## Considered

- Checks in the reports: errors are found late, by the wrong people.
- Warnings instead of stops: nothing is delayed, but warnings get ignored.

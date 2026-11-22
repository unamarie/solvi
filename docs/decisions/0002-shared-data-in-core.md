# 2. Shared data lives once, in core, read through shortcuts

Status: accepted, November 2026

## Context

Almost every domain needs customers, sites, products and weather. Copies drift apart.

## Decision

Core owns the shared master data. Other domains read it through OneLake shortcuts and never copy it. [SHORTCUTS.md](../../notebooks/SHORTCUTS.md) lists every shortcut.

## Consequences

- Every app sees the same customer, site and product.
- Readers depend on core's tables. Core's gate checks keys and columns before it publishes.
- Core runs first in the nightly pipeline.

## Considered

- Copy core tables into each domain: no dependency at run time, but each copy is out of date the day after.

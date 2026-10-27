# Maç Analiz — current project specification

Updated October 27, 2026 for the local `0.1.0-rc.1` source candidate. This replaces generated historical notes with unsupported dates and obsolete setup assumptions. It does not claim a published release, live validation or adoption.

## Intended behavior

- Turkish football match list, match details, scores/status and recent form.
- Deterministic analysis text using recent team results, head-to-head data and heuristic rules; this is not validated forecasting.
- Loading, error and empty states; live detail refresh every 30 seconds.
- Dark interface with responsive cards, system fonts and local CSS gradients.
- No authentication, payment or betting flow.

## Architecture and contracts

- Next.js 16 / React 19 / Tailwind frontend on loopback port 3000.
- FastAPI / httpx backend on loopback port 8001, using football-data.org v4.
- Frontend `/api` requests use the configured server-side Next proxy by default.
- GET endpoints: `/api/health`, `/api/matches`, `/api/matches/form`, `/api/match/{id}`, `/api/match/{id}/analysis`.
- Provider keys remain backend-only. Match data uses a bounded per-worker 120-second monotonic TTL/LRU cache; defaults are 256 entries and four active provider calls with a two-second slot wait.
- Form-list primary failures return explicit errors; successful empty schedules remain successful empty results.

## Maintenance and boundaries

See the [README](../README.md) for reproducible setup and [development notes](../docs/development.md) for test boundaries. Tests use synthetic fixtures and mocked responses; no provider key or real dataset is needed. CI covers Windows/Linux backend contracts and Linux frontend build/browser checks. It runs on pull requests, pushes to `main` and manual dispatch; all three jobs passed after PR #1 merged.

Original-code MIT scope, owner provenance declarations and residual uncertainty are recorded in [rights and assets](../docs/rights-and-assets.md). Dependency icons retain separate notices. Provider data and graphics are not MIT-licensed. No remote photos, fonts, logos, captured reports or compiled output belong in the source candidate.

Analysis now identifies unavailable optional sources without discarding usable output, and partial results can recover on reload. Remaining work: provider rate/backoff policy and in-flight deduplication, deeper match schemas, homepage form-availability messaging, authorized live-provider compatibility and complete manual accessibility checks. See the [release plan](../docs/release-plan.md) before publication.

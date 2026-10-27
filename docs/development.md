# Development and offline tests

The app remains Next.js plus FastAPI. Browser requests use the existing `/api` paths; Next.js rewrites them to the configured backend. Only the backend receives the provider key. The existing live refresh interval remains 30 seconds.

## Locks

Use Python 3.12 and `backend/requirements.txt` with `--require-hashes`. To deliberately update the lock, install `pip-tools==7.6.2` in a tooling environment and run:

```sh
python -m piptools compile --upgrade --generate-hashes --strip-extras --output-file backend/requirements.txt backend/requirements.in
```

Review versions, notices and advisories; do not regenerate locks during CI. Exact npm direct versions and package-lock.json must agree. Use `npm ci --ignore-scripts`. The webpack production build preserves the existing Tailwind/PostCSS setup.

## Test boundaries

Backend unittest tests use the in-process FastAPI client and httpx MockTransport. All provider routes are explicitly mocked, credentials are synthetic, and unexpected fixture requests fail even if optional application handling catches them. Tests cover contracts, statistics, errors, retry, cache expiry and CORS rejection.

From `frontend`, `npm run test:config` checks the local proxy target and rejects credentials, non-HTTP schemes, queries and fragments. `npm test` runs the separate production-browser suite after a build.

Browser tests run the production frontend with invented API responses and block external requests. They cover navigation, analysis, forms, empty/error/retry states, narrow-screen layout and selected accessibility rules. They do not prove full WCAG compliance or live provider compatibility.

Install tooling/browsers once with network access; test execution requires only loopback. Some Windows shell sandboxes block Python asyncio's socketpair. Run the mocked suite in a normal authorized terminal instead. Use a writable local TEMP/TMP if a sandbox prevents browser downloads; do not replace fixtures with a live service to work around it.

## CI and limits

CI tests Python on Windows/Linux and builds/tests the frontend on Linux. It uses pinned action revisions, read-only permissions, no secrets, and no publication job. All three jobs passed on the [PR #1 merge commit](https://github.com/doksanbes/mac-analiz/actions/runs/40546110561). The workflow runs for pull requests, pushes to `main` and manual `workflow_dispatch`; a feature-branch push alone does not trigger it. Runtime minor selections in CI float to security patches; dependency versions/hashes are locked.

The analysis API includes `data_warnings`, an ordered list of unavailable-source codes: `home_recent`, `away_recent`, `head_to_head`. The detail page renders their Turkish labels in a status message. A valid empty history has no warning. Optional failures return `None` internally rather than a successful empty list; malformed top-level optional payloads are unavailable. Primary-match failures still return errors. Only complete aggregate responses are cached; successful individual sources retain their normal cache. Failed optional requests can be attempted again on the next request, without automatic retries or backoff.

## Provider load and cache controls

Each FastAPI lifespan owns one HTTPX client/connection pool and an asyncio semaphore, avoiding per-request client creation and cross-loop semaphore reuse. Defaults: four active provider calls, a two-second slot wait, and 256 cache entries per worker. See README/environment examples for supported ranges; restart after changes. HTTP operation timeouts remain 15 seconds for primary requests and 10 seconds for optional history, separate from slot waiting. Queue timeout is a sanitized 503 for primary requests; optional callers retain their partial-data contract. Active permits are released in `finally`, including errors and cancellation. The client closes at lifespan shutdown. ASGI test clients must run the application lifespan.

The 120-second cache uses monotonic timestamps. Reads delete an expired requested entry and mark live entries recently used. Writes prune all expired entries before inserting/updating, then evict least-recently-used entries until within the cap. Empty lists/objects remain valid values. Partial aggregates and failures are still not cached. Expiry does not require a background task; an idle cache can retain expired entries until the next read/write, but entry count remains bounded. Pruning is O(entry cap) on writes, with a default cap of 256.

The limits are per worker/process: multiple workers multiply potential provider concurrency and have independent caches. They do not limit calls per minute, deduplicate concurrent misses, bound all ASGI tasks/waiters or enforce a cache byte budget. No Redis, scheduler, paid service or new dependency is used. Regression tests use event barriers and MockTransport to exercise concurrent misses, saturation, active/queued cancellation, failure recovery, empty histories, expiry and LRU eviction without live provider traffic.

Remaining work includes requests-per-minute/backoff policy, in-flight deduplication/admission control where needed, deeper provider schemas, homepage form-availability messaging and full manual accessibility review. No deployment or forecast-accuracy claim follows from fixture tests.

[Back to README](../README.md)

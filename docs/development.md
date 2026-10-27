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

## CI draft and limits

Proposed CI tests Python on Windows/Linux and builds/tests the frontend on Linux. It uses pinned action revisions, read-only permissions, no secrets, and no publication job. It has not been pushed or run on GitHub. Runtime minor selections in CI float to security patches; dependency versions/hashes are locked.

Remaining work includes explicit optional-data warnings, bounded request concurrency/cache size, stronger provider schemas, and full manual accessibility review. No deployment or forecast-accuracy claim follows from fixture tests.

[Back to README](../README.md)

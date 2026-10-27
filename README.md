# Maç Analiz

A Turkish football match browser and rule-based analysis app using FastAPI, Next.js and football-data.org. Match lists, scores, recent form, analysis and live refresh remain the intended functionality. No authentication, payment or betting flow is added.

**Status:** source candidate `0.1.0-rc.1` is merged into `main`; no tag or GitHub release has been published. No release or adoption is claimed. See [rights and assets](docs/rights-and-assets.md) and the [changelog](CHANGELOG.md).

## License

The original application source, configuration, tests and documentation are offered under the [MIT License](LICENSE), copyright 2026 doksanbes, to the extent the author holds rights in them. The owner declares this was a new personal Emergent project with no supplied third-party materials or other rights holders; this is a declaration, not proof that every generated fragment is unrestricted.

Dependencies and their embedded code, Lucide/Feather icon designs, provider responses, logos, photos, fonts and other third-party material retain their own terms and are outside this original-code grant. Preserve [third-party notices](THIRD_PARTY_NOTICES.md). The license does not cover Emergent's platform or brand, or grant rights to removed historical build/data artifacts. This candidate contains source only, without bundled dependencies, data or compiled output.

## Requirements

Use Python 3.12 and a supported, security-patched Node.js 24 release with npm. Live data requires your own football-data.org key and compliance with your plan. Tests require no key and use synthetic data. Dependency/browser installation requires internet; test execution requires local loopback only.

Supervisor, a cloud IDE, Docker and global Python packages are not needed. The proposed frontend uses Next.js 16 and React 19. Python requirements are hash-pinned; npm dependencies have a lockfile.

## Windows setup

Run from the repository root in PowerShell:

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --require-hashes -r backend\requirements.txt
if (-not (Test-Path backend\.env)) { Copy-Item backend\.env.example backend\.env }
if (-not (Test-Path frontend\.env.local)) { Copy-Item frontend\.env.example frontend\.env.local }
cd frontend
npm.cmd ci --ignore-scripts
```

For live use, put your own key in `backend/.env`. Keep it server-side; never put it in `NEXT_PUBLIC_*`, a report or a commit.

Start the backend from the repository root in one terminal:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.server:app --reload --host 127.0.0.1 --port 8001
```

In another terminal, run `npm.cmd run dev` from `frontend`. Open [the local app](http://127.0.0.1:3000). Next.js proxies `/api` to the backend, so a separate browser API URL is unnecessary. Without a key, health and offline tests work; live requests return 503.

## Linux and macOS setup

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r backend/requirements.txt
test -f backend/.env || cp backend/.env.example backend/.env
test -f frontend/.env.local || cp frontend/.env.example frontend/.env.local
cd frontend
npm ci --ignore-scripts
```

From the repository root, start `.venv/bin/python -m uvicorn backend.server:app --reload --host 127.0.0.1 --port 8001`. Run `npm run dev` from `frontend` in a second terminal. Windows/Linux backend and Linux frontend CI passed after [PR #1](https://github.com/doksanbes/mac-analiz/pull/1) merged ([verified run](https://github.com/doksanbes/mac-analiz/actions/runs/40546110561)). macOS setup has not been validated by CI.

## Offline tests and build

From the repository root on Windows:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
.\.venv\Scripts\python.exe -m compileall -q backend tests
cd frontend
npm.cmd run test:config
npm.cmd run build
npx.cmd playwright install chromium
npm.cmd test
```

On Linux/macOS, use `.venv/bin/python`, `npm` and `npx`. Tests use invented matches and mocked provider responses; no live data is exported. Browser tests start/stop a production frontend on port 3000, which must be free. The old `backend_test.py` entry point now runs the offline suite instead of a hosted preview.

For a local production check, run `npm run build` then `npm start` from `frontend`. Start uses `next start`, not the development server. Public deployment requires separate review and approval. See [development](docs/development.md).

## Configuration

| Variable | Scope and purpose |
| --- | --- |
| `FOOTBALL_DATA_API_TOKEN` | Backend-only key; environment or `backend/.env`; existing environment wins |
| `ALLOWED_ORIGINS` | Direct-browser backend access; comma-separated origins; defaults to localhost/127.0.0.1 on port 3000; no cookie credentials |
| `PROVIDER_MAX_CONCURRENCY` | Maximum active provider calls per backend worker; integer 1–32, default 4 |
| `PROVIDER_QUEUE_TIMEOUT` | Seconds to wait for a provider slot; greater than 0 and at most 30, default 2 |
| `CACHE_MAX_ENTRIES` | Per-worker cache entry cap; integer 1–4096, default 256 |
| `BACKEND_URL` | Server-only Next.js proxy target; defaults to `http://127.0.0.1:8001`; no embedded credentials/query/fragment; rebuild after changing |
| `NEXT_PUBLIC_BACKEND_URL` | Optional public browser override; leave blank for proxy; embedded at build time; never a secret |

Examples in each service's `.env.example` contain no working keys. Restart the backend after changing load-control settings; invalid limits fail at startup.

## Endpoints

| GET path | Purpose |
| --- | --- |
| `/api/health` | Status and token-configured flag, without contacting the provider |
| `/api/matches` | Provider match list |
| `/api/matches/form` | Recent form for its teams |
| `/api/match/{id}` | Match details |
| `/api/match/{id}/analysis` | Rule-based summary and form |

Form retrieval now shares match-list error handling: rate limits return 429, timeouts 504, transport/invalid-response failures 502. Successful empty schedules still produce 200 with an empty form object. Failures are not cached as successful results.

## Data and limitations

Football data provided by the [Football-Data.org API](https://www.football-data.org/). Live operation requires your own registered, application-scoped key and a plan covering the endpoints you use. Follow the [provider terms](https://www.football-data.org/about), rate/fair-use limits and attribution requirement. Provider responses are not MIT-licensed or an open dataset. The terms restrict referencing obtained data after subscription cancellation and require graphics-owner permission for logos/photos. Do not commit keys, cache dumps or live response fixtures. Unverified images/fonts, crests, generated builds and captured reports are excluded from this source candidate. The UI uses names, local CSS and system fonts.

Analysis uses deterministic rules, not validated predictions. If recent-team or head-to-head requests fail, the detail page identifies the unavailable sources while keeping usable analysis visible. The API adds `data_warnings` codes (`home_recent`, `away_recent`, `head_to_head`); successful empty histories are not failures. Partial analysis/form results are not cached, so a later reload can recover; successful source responses still use the 120-second cache. A lifespan-owned HTTP client and semaphore cap active provider calls per worker. Waiting longer than the configured queue timeout returns 503 for primary data or existing missing-source warnings for optional analysis data. Permits are released on failure/cancellation. The in-memory cache retains its 120-second TTL, uses monotonic time, removes expired entries on reads/writes and evicts the least recently used entry at capacity. There is no automatic retry, requests-per-minute limiter, rate-limit backoff or cross-worker coordination. Entry count is bounded, not response bytes or total incoming tasks. Deeper provider schemas, homepage availability messaging and full accessibility review remain future work. No adoption or accuracy claims are made.

See [the release plan](docs/release-plan.md). New changes may be reviewed through PRs; merge, tag, release and deployment require their own approval. CI has no publish job.

"""Offline contracts using invented clubs, IDs and match results only."""
import copy
import asyncio
import os
import unittest
from unittest.mock import patch

import httpx
from fastapi.testclient import TestClient
from backend import server

REAL_ASYNC_CLIENT = httpx.AsyncClient


def match(match_id=9001, home=101, away=202, score=(2, 1), status='FINISHED'):
    return {
        'id': match_id, 'status': status, 'utcDate': '2026-10-01T18:00:00Z',
        'homeTeam': {'id': home, 'name': 'Example North', 'shortName': 'North'},
        'awayTeam': {'id': away, 'name': 'Example South', 'shortName': 'South'},
        'competition': {'id': 77, 'name': 'Example League'},
        'score': {'fullTime': {'home': score[0], 'away': score[1]}},
    }


class OfflineAPI(unittest.TestCase):
    def setUp(self):
        server._cache.clear()
        self.requests = []
        self.fixture_errors = []
        self.env = patch.dict(os.environ, {'FOOTBALL_DATA_API_TOKEN': 'offline-fixture-token'})
        self.env.start()
        self.network = patch('socket.create_connection', side_effect=AssertionError('Real network is forbidden'))
        self.network.start()

    def tearDown(self):
        self.network.stop()
        self.env.stop()
        server._cache.clear()
        self.assertEqual(self.fixture_errors, [])

    def client(self, handler):
        def fixture(request):
            self.requests.append(request)
            try:
                self.assertEqual(request.url.host, 'api.football-data.org')
                self.assertEqual(request.headers['X-Auth-Token'], 'offline-fixture-token')
                return handler(request)
            except AssertionError as error:
                self.fixture_errors.append(str(error))
                raise
        transport = httpx.MockTransport(fixture)
        return patch.object(server.httpx, 'AsyncClient', side_effect=lambda **kwargs: REAL_ASYNC_CLIENT(transport=transport, **kwargs))

    def success(self, request):
        path = request.url.path
        if path == '/v4/matches':
            return httpx.Response(200, json={'matches': [match()]})
        if path == '/v4/matches/9001':
            return httpx.Response(200, json=match())
        if path in ('/v4/teams/101/matches', '/v4/teams/202/matches'):
            self.assertEqual(dict(request.url.params), {'status': 'FINISHED', 'limit': '15'})
            return httpx.Response(200, json={'matches': [match()]})
        if path == '/v4/matches/9001/head2head':
            self.assertEqual(dict(request.url.params), {'limit': '10'})
            return httpx.Response(200, json={'matches': []})
        raise AssertionError('Unexpected fixture request: ' + path)

    def test_health_does_not_contact_provider(self):
        with self.client(lambda _: self.fail('Health must not make requests')), TestClient(server.app) as client:
            self.assertEqual(client.get('/api/health').json(), {'status': 'ok', 'api_token_configured': True})
        self.assertEqual(self.requests, [])

    def test_missing_credentials_are_actionable_without_leaking_a_token(self):
        with patch.dict(os.environ, {'FOOTBALL_DATA_API_TOKEN': ''}), self.client(self.success), TestClient(server.app) as client:
            response = client.get('/api/matches')
        self.assertEqual(response.status_code, 503)
        self.assertEqual(self.requests, [])

    def test_matches_and_details_keep_the_existing_response_contract(self):
        with self.client(self.success), TestClient(server.app) as client:
            self.assertEqual(client.get('/api/matches').json(), {'matches': [match()]})
            self.assertEqual(client.get('/api/match/9001').json(), match())
            client.get('/api/matches')
        self.assertEqual(len(self.requests), 2)

    def test_forms_preserve_home_and_away_results(self):
        with self.client(self.success), TestClient(server.app) as client:
            response = client.get('/api/matches/form')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {'9001': {'home_form': 'G', 'away_form': 'M'}})

    def test_successful_empty_match_list_is_a_success(self):
        with self.client(lambda _: httpx.Response(200, json={'matches': []})), TestClient(server.app) as client:
            response = client.get('/api/matches/form')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {})

    def test_form_rate_limit_is_not_reported_as_empty_success(self):
        with self.client(lambda _: httpx.Response(429, json={'detail': 'provider text'})), TestClient(server.app) as client:
            response = client.get('/api/matches/form')
        self.assertEqual(response.status_code, 429)
        self.assertNotIn('provider text', response.text)
        self.assertNotIn('all_form', server._cache)

    def test_form_timeout_is_not_reported_as_empty_success(self):
        def timeout(request):
            raise httpx.ReadTimeout('synthetic timeout', request=request)
        with self.client(timeout), TestClient(server.app) as client:
            response = client.get('/api/matches/form')
        self.assertEqual(response.status_code, 504)

    def test_form_connection_failure_is_not_reported_as_empty_success(self):
        def disconnected(request):
            raise httpx.ConnectError('synthetic transport detail', request=request)
        with self.client(disconnected), TestClient(server.app) as client:
            response = client.get('/api/matches/form')
        self.assertEqual(response.status_code, 502)
        self.assertNotIn('synthetic transport detail', response.text)

    def test_malformed_provider_json_is_a_gateway_error(self):
        with self.client(lambda _: httpx.Response(200, text='not json')), TestClient(server.app) as client:
            response = client.get('/api/matches/form')
        self.assertEqual(response.status_code, 502)

    def test_invalid_match_list_shape_is_not_cached(self):
        for data in ([], {'matches': None}, {'matches': 'invalid'}, {}):
            with self.subTest(data=data), self.client(lambda _: httpx.Response(200, json=data)), TestClient(server.app) as client:
                self.assertEqual(client.get('/api/matches/form').status_code, 502)
            self.assertEqual(server._cache, {})

    def test_failed_request_can_be_retried_immediately(self):
        with self.client(lambda _: httpx.Response(429)), TestClient(server.app) as client:
            self.assertEqual(client.get('/api/matches/form').status_code, 429)
        with self.client(self.success), TestClient(server.app) as client:
            self.assertEqual(client.get('/api/matches/form').json()['9001']['home_form'], 'G')

    def test_default_cors_does_not_trust_unrelated_origins(self):
        with self.client(self.success), TestClient(server.app) as client:
            allowed = client.get('/api/health', headers={'Origin': 'http://localhost:3000'})
            rejected = client.get('/api/health', headers={'Origin': 'https://untrusted.invalid'})
        self.assertEqual(allowed.headers.get('access-control-allow-origin'), 'http://localhost:3000')
        self.assertNotIn('access-control-allow-origin', rejected.headers)
        self.assertNotIn('access-control-allow-credentials', allowed.headers)

    def test_analysis_remains_available_with_synthetic_data(self):
        with self.client(self.success), TestClient(server.app) as client:
            response = client.get('/api/match/9001/analysis')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['home_form'], 'G')
        self.assertEqual(response.json()['away_form'], 'M')
        self.assertEqual(set(response.json()), {'hizli_bakis', 'home_form', 'away_form', 'mac_ozeti',
                                              'kg_analizi', 'gol_analizi', 'ms_egilimi', 'risk_notu', 'data_warnings'})

    def test_invalid_match_identifier_is_rejected_without_provider_call(self):
        with self.client(self.success), TestClient(server.app) as client:
            self.assertEqual(client.get('/api/match/not-a-number').status_code, 422)
        self.assertEqual(self.requests, [])

    def test_analysis_warns_when_optional_sources_fail(self):
        def failure(kind, request):
            if request.url.path == '/v4/matches/9001':
                return self.success(request)
            if kind == 'timeout':
                raise httpx.ReadTimeout('synthetic private transport detail', request=request)
            if kind == 'transport':
                raise httpx.ConnectError('synthetic private transport detail', request=request)
            if kind == 'json':
                return httpx.Response(200, text='not json')
            if kind == 'shape':
                return httpx.Response(200, json={'matches': None})
            return httpx.Response(kind, json={'detail': 'synthetic private provider detail'})

        for kind in (403, 429, 'timeout', 'transport', 'json', 'shape'):
            server._cache.clear()
            with self.subTest(kind=kind):
                with self.client(lambda request: failure(kind, request)), TestClient(server.app) as client:
                    response = client.get('/api/match/9001/analysis')
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.json()['data_warnings'], ['home_recent', 'away_recent', 'head_to_head'])
                self.assertIn('mac_ozeti', response.json())
                self.assertNotIn('synthetic private', response.text)
                self.assertNotIn('analysis_9001', server._cache)

    def test_analysis_identifies_only_the_unavailable_source(self):
        def handler(request):
            if request.url.path == '/v4/teams/101/matches':
                return httpx.Response(429)
            return self.success(request)
        with self.client(handler), TestClient(server.app) as client:
            data = client.get('/api/match/9001/analysis').json()
        self.assertEqual(data['data_warnings'], ['home_recent'])
        self.assertEqual(data['home_form'], '')
        self.assertEqual(data['away_form'], 'M')

    def test_valid_empty_history_is_not_a_provider_failure(self):
        def handler(request):
            if request.url.path == '/v4/matches/9001':
                return self.success(request)
            return httpx.Response(200, json={'matches': []})
        with self.client(handler), TestClient(server.app) as client:
            data = client.get('/api/match/9001/analysis').json()
        self.assertEqual(data['data_warnings'], [])
        self.assertEqual(data['home_form'], '')
        self.assertIn('analysis_9001', server._cache)

    def test_partial_analysis_can_recover_without_waiting_for_cache_expiry(self):
        def handler(request):
            if request.url.path == '/v4/teams/101/matches':
                return httpx.Response(429)
            return self.success(request)
        with self.client(handler), TestClient(server.app) as client:
            self.assertEqual(client.get('/api/match/9001/analysis').json()['data_warnings'], ['home_recent'])
        with self.client(self.success), TestClient(server.app) as client:
            data = client.get('/api/match/9001/analysis').json()
        self.assertEqual(data['data_warnings'], [])
        self.assertEqual(data['home_form'], 'G')
        self.assertIn('analysis_9001', server._cache)

    def test_partial_forms_keep_the_contract_and_can_recover(self):
        def handler(request):
            if request.url.path == '/v4/teams/101/matches':
                return httpx.Response(429)
            return self.success(request)
        with self.client(handler), TestClient(server.app) as client:
            self.assertEqual(client.get('/api/matches/form').json(), {'9001': {'home_form': '', 'away_form': 'M'}})
        self.assertNotIn('all_form', server._cache)
        with self.client(self.success), TestClient(server.app) as client:
            self.assertEqual(client.get('/api/matches/form').json()['9001']['home_form'], 'G')


class Statistics(unittest.TestCase):
    def test_stats_cover_home_away_draw_missing_score_and_unfinished_matches(self):
        matches = [match(), match(9002, 202, 101, (0, 3)), match(9003, score=(1, 1)),
                   match(9004, score=(None, None)), match(9005, status='TIMED')]
        original = copy.deepcopy(matches)
        stats = server.calc_team_stats(101, matches)
        self.assertEqual((stats['played'], stats['wins'], stats['draws'], stats['losses']), (3, 2, 1, 0))
        self.assertEqual((stats['gf'], stats['ga'], stats['form_str']), (6, 2, 'GGB'))
        self.assertEqual(matches, original)

    def test_empty_stats_and_missing_h2h_are_supported(self):
        self.assertEqual(server.calc_team_stats(101, [])['played'], 0)
        self.assertIsNone(server.calc_h2h_stats(101, None))
        self.assertIsNone(server.detect_two_leg(match(), None))

    def test_cache_expires_at_the_boundary(self):
        server._cache.clear()
        with patch.object(server.time, 'monotonic', return_value=100):
            server.cache_set('synthetic', {'example': True})
        with patch.object(server.time, 'monotonic', return_value=219):
            self.assertIsNotNone(server.cache_get('synthetic'))
        with patch.object(server.time, 'monotonic', return_value=220):
            self.assertIsNone(server.cache_get('synthetic'))
        server._cache.clear()


class BoundedCache(unittest.TestCase):
    def setUp(self):
        server._cache.clear()

    def tearDown(self):
        server._cache.clear()

    def test_capacity_evicts_the_least_recently_used_entry(self):
        with patch.object(server, 'CACHE_MAX_ENTRIES', 2):
            server.cache_set('a', 'first')
            server.cache_set('b', 'second')
            self.assertEqual(server.cache_get('a'), 'first')
            server.cache_set('c', 'third')
            self.assertIsNone(server.cache_get('b'))
            self.assertEqual(server.cache_get('a'), 'first')
            self.assertEqual(server.cache_get('c'), 'third')
            self.assertEqual(len(server._cache), 2)

    def test_write_prunes_expired_entries_before_evicting_live_data(self):
        with patch.object(server, 'CACHE_MAX_ENTRIES', 2):
            with patch.object(server.time, 'monotonic', return_value=100):
                server.cache_set('expired', [])
            with patch.object(server.time, 'monotonic', return_value=150):
                server.cache_set('live', {})
            with patch.object(server.time, 'monotonic', return_value=200):
                self.assertEqual(server.cache_get('expired'), [])
            with patch.object(server.time, 'monotonic', return_value=220):
                server.cache_set('new', False)
                self.assertNotIn('expired', server._cache)
                self.assertEqual(server.cache_get('live'), {})
                self.assertIs(server.cache_get('new'), False)

    def test_expired_read_removes_the_entry(self):
        with patch.object(server.time, 'monotonic', return_value=100):
            server.cache_set('entry', [])
        with patch.object(server.time, 'monotonic', return_value=220):
            self.assertIsNone(server.cache_get('entry'))
            self.assertNotIn('entry', server._cache)

    def test_updates_and_many_distinct_keys_never_exceed_capacity(self):
        with patch.object(server, 'CACHE_MAX_ENTRIES', 3):
            for i in range(40):
                server.cache_set(str(i), i)
                self.assertLessEqual(len(server._cache), 3)
            server.cache_set('39', [])
            self.assertEqual(len(server._cache), 3)
            self.assertEqual(server.cache_get('39'), [])
            self.assertEqual(server.cache_get('38'), 38)

    def test_wall_clock_changes_do_not_expire_fresh_data(self):
        with patch.object(server.time, 'monotonic', return_value=100), patch.object(server.time, 'time', return_value=100):
            server.cache_set('entry', {})
        with patch.object(server.time, 'monotonic', return_value=101), patch.object(server.time, 'time', return_value=999999):
            self.assertEqual(server.cache_get('entry'), {})


class ProviderLoad(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        server._cache.clear()
        self.env = patch.dict(os.environ, {'FOOTBALL_DATA_API_TOKEN': 'offline-fixture-token'})
        self.env.start()
        self.network = patch('socket.create_connection', side_effect=AssertionError('Real network is forbidden'))
        self.network.start()
        self.provider_clients = []

    async def asyncTearDown(self):
        self.network.stop()
        self.env.stop()
        server._cache.clear()
        self.assertTrue(all(client.is_closed for client in self.provider_clients))

    def provider(self, handler):
        async def fixture(request):
            self.assertEqual(request.url.host, 'api.football-data.org')
            self.assertEqual(request.headers['X-Auth-Token'], 'offline-fixture-token')
            return await handler(request)
        def create(**kwargs):
            client = REAL_ASYNC_CLIENT(transport=httpx.MockTransport(fixture))
            self.provider_clients.append(client)
            return client
        return patch.object(server.httpx, 'AsyncClient', side_effect=create)

    def api(self):
        return REAL_ASYNC_CLIENT(transport=httpx.ASGITransport(app=server.app), base_url='http://offline.test')

    async def test_concurrent_misses_respect_one_shared_provider_limit(self):
        active = peak = 0
        filled, release = asyncio.Event(), asyncio.Event()
        async def handler(request):
            nonlocal active, peak
            active += 1
            peak = max(peak, active)
            if active == 2:
                filled.set()
            try:
                await release.wait()
                return httpx.Response(200, json=match(int(request.url.path.rsplit('/', 1)[-1])))
            finally:
                active -= 1
        with patch.object(server, 'PROVIDER_MAX_CONCURRENCY', 2), patch.object(server, 'CACHE_MAX_ENTRIES', 3), self.provider(handler):
            async with server.lifespan(server.app), self.api() as api:
                tasks = [asyncio.create_task(api.get(f'/api/match/{9001+i}')) for i in range(8)]
                try:
                    await asyncio.wait_for(filled.wait(), 2)
                    await asyncio.sleep(0)
                    self.assertEqual(peak, 2)
                finally:
                    release.set()
                    responses = await asyncio.gather(*tasks)
                self.assertTrue(all(response.status_code == 200 for response in responses))
                self.assertEqual(peak, 2)
                self.assertEqual(len(self.provider_clients), 1)
                self.assertEqual(len(server._cache), 3)

    async def test_queue_timeout_is_not_cached_and_next_request_can_recover(self):
        started, release = asyncio.Event(), asyncio.Event()
        paths = []
        async def handler(request):
            paths.append(request.url.path)
            if request.url.path.endswith('/9001'):
                started.set()
                await release.wait()
            return httpx.Response(200, json=match())
        with patch.object(server, 'PROVIDER_MAX_CONCURRENCY', 1), patch.object(server, 'PROVIDER_QUEUE_TIMEOUT', 0.05), self.provider(handler):
            async with server.lifespan(server.app), self.api() as api:
                held = asyncio.create_task(api.get('/api/match/9001'))
                try:
                    await asyncio.wait_for(started.wait(), 2)
                    overloaded = await asyncio.wait_for(api.get('/api/match/9002'), 2)
                    self.assertEqual(overloaded.status_code, 503)
                    self.assertEqual(paths, ['/v4/matches/9001'])
                    self.assertNotIn('match_9002', server._cache)
                finally:
                    release.set()
                    await held
                self.assertEqual((await api.get('/api/match/9002')).status_code, 200)

    async def test_failed_provider_calls_release_capacity(self):
        async def handler(request):
            if request.url.path.endswith('/9002'):
                return httpx.Response(200, json=match())
            if kind == 'timeout':
                raise httpx.ReadTimeout('synthetic private detail', request=request)
            if kind == 'transport':
                raise httpx.ConnectError('synthetic private detail', request=request)
            if kind == 'json':
                return httpx.Response(200, text='not json')
            return httpx.Response(429)
        with patch.object(server, 'PROVIDER_MAX_CONCURRENCY', 1), self.provider(handler):
            async with server.lifespan(server.app), self.api() as api:
                for kind, status in [('timeout', 504), ('transport', 502), ('json', 502), ('rate_limit', 429)]:
                    server._cache.clear()
                    with self.subTest(kind=kind):
                        failed = await api.get('/api/match/9001')
                        self.assertEqual(failed.status_code, status)
                        self.assertNotIn('synthetic private', failed.text)
                        self.assertNotIn('match_9001', server._cache)
                        self.assertEqual((await asyncio.wait_for(api.get('/api/match/9002'), 2)).status_code, 200)

    async def test_cancellation_releases_capacity(self):
        started = asyncio.Event()
        async def handler(request):
            if request.url.path.endswith('/9001'):
                started.set()
                await asyncio.Event().wait()
            return httpx.Response(200, json=match())
        with patch.object(server, 'PROVIDER_MAX_CONCURRENCY', 1), self.provider(handler):
            async with server.lifespan(server.app), self.api() as api:
                task = asyncio.create_task(api.get('/api/match/9001'))
                await asyncio.wait_for(started.wait(), 2)
                task.cancel()
                with self.assertRaises(asyncio.CancelledError):
                    await task
                self.assertNotIn('match_9001', server._cache)
                self.assertEqual((await asyncio.wait_for(api.get('/api/match/9002'), 2)).status_code, 200)

    async def test_cancelling_a_waiter_does_not_release_another_requests_slot(self):
        started, release = asyncio.Event(), asyncio.Event()
        paths = []
        async def handler(request):
            paths.append(request.url.path)
            if request.url.path.endswith('/9001'):
                started.set()
                await release.wait()
            return httpx.Response(200, json=match())
        with patch.object(server, 'PROVIDER_MAX_CONCURRENCY', 1), patch.object(server, 'PROVIDER_QUEUE_TIMEOUT', 0.1), self.provider(handler):
            async with server.lifespan(server.app), self.api() as api:
                held = asyncio.create_task(api.get('/api/match/9001'))
                try:
                    await asyncio.wait_for(started.wait(), 2)
                    waiter = asyncio.create_task(api.get('/api/match/9002'))
                    await asyncio.sleep(0)
                    waiter.cancel()
                    with self.assertRaises(asyncio.CancelledError):
                        await waiter
                    self.assertEqual((await api.get('/api/match/9003')).status_code, 503)
                    self.assertEqual(paths, ['/v4/matches/9001'])
                finally:
                    release.set()
                    await held
                self.assertEqual((await api.get('/api/match/9002')).status_code, 200)

    async def test_optional_overload_warns_then_valid_empty_history_recovers(self):
        started, release = asyncio.Event(), asyncio.Event()
        paths = []
        async def handler(request):
            paths.append(request.url.path)
            if request.url.path == '/v4/matches/9002':
                started.set()
                await release.wait()
                return httpx.Response(200, json=match(9002))
            return httpx.Response(200, json={'matches': []})
        server.cache_set('match_9001', match())
        with patch.object(server, 'PROVIDER_MAX_CONCURRENCY', 1), patch.object(server, 'PROVIDER_QUEUE_TIMEOUT', 0.1), self.provider(handler):
            async with server.lifespan(server.app), self.api() as api:
                held = asyncio.create_task(api.get('/api/match/9002'))
                try:
                    await asyncio.wait_for(started.wait(), 2)
                    partial = await api.get('/api/match/9001/analysis')
                    self.assertEqual(partial.status_code, 200)
                    self.assertEqual(partial.json()['data_warnings'], ['home_recent', 'away_recent', 'head_to_head'])
                    self.assertNotIn('analysis_9001', server._cache)
                finally:
                    release.set()
                    await held
                recovered = await api.get('/api/match/9001/analysis')
                self.assertEqual(recovered.json()['data_warnings'], [])
                self.assertEqual(recovered.json()['home_form'], '')
                self.assertIn('analysis_9001', server._cache)
                previous_calls = len(paths)
                self.assertEqual((await api.get('/api/match/9001/analysis')).json(), recovered.json())
                self.assertEqual(len(paths), previous_calls)


class LimitConfiguration(unittest.TestCase):
    def test_integer_limit_configuration_fails_fast(self):
        for value in ('0', '-1', '33', 'not-a-number'):
            with self.subTest(value=value), patch.dict(os.environ, {'PROVIDER_MAX_CONCURRENCY': value}):
                with self.assertRaises(ValueError):
                    server.bounded_int_setting('PROVIDER_MAX_CONCURRENCY', 4, 32)
        with patch.dict(os.environ, {'CACHE_MAX_ENTRIES': '3'}):
            self.assertEqual(server.bounded_int_setting('CACHE_MAX_ENTRIES', 256, 4096), 3)


if __name__ == '__main__':
    unittest.main()

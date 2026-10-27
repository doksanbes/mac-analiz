"""Offline contracts using invented clubs, IDs and match results only."""
import copy
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
        with patch.object(server.time, 'time', return_value=100):
            server.cache_set('synthetic', {'example': True})
        with patch.object(server.time, 'time', return_value=219):
            self.assertIsNotNone(server.cache_get('synthetic'))
        with patch.object(server.time, 'time', return_value=220):
            self.assertIsNone(server.cache_get('synthetic'))
        server._cache.clear()


if __name__ == '__main__':
    unittest.main()

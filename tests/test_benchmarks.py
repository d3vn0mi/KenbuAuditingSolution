class TestBenchmarkBrowsing:
    def test_list_benchmarks(self, auth_client, seed_data):
        resp = auth_client.get('/benchmarks/')
        assert resp.status_code == 200
        assert b'Test CIS Benchmark' in resp.data

    def test_benchmark_detail(self, auth_client, seed_data):
        bid = seed_data['benchmark'].id
        resp = auth_client.get(f'/benchmarks/{bid}')
        assert resp.status_code == 200
        assert b'Test Section' in resp.data

    def test_section_detail(self, auth_client, seed_data):
        bid = seed_data['benchmark'].id
        sid = seed_data['section'].id
        resp = auth_client.get(f'/benchmarks/{bid}/section/{sid}')
        assert resp.status_code == 200
        assert b'Test Check 1.1' in resp.data

    def test_check_detail(self, auth_client, seed_data):
        check_id = seed_data['checks'][0].id
        resp = auth_client.get(f'/checks/{check_id}')
        assert resp.status_code == 200
        assert b'audit 1.1' in resp.data
        assert b'Remediation for 1.1' in resp.data

    def test_search_by_keyword(self, auth_client, seed_data):
        resp = auth_client.get('/checks/search?q=Check+1.1')
        assert resp.status_code == 200
        assert b'Test Check 1.1' in resp.data

    def test_search_by_level(self, auth_client, seed_data):
        resp = auth_client.get('/checks/search?level=2')
        assert resp.status_code == 200
        assert b'Test Check 1.2' in resp.data
        assert b'Test Check 1.1' not in resp.data

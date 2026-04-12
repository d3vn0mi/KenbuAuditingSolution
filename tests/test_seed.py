import os
import pytest
from app.models import Platform, Benchmark, BenchmarkSection, Check
from app.utils.seed import seed_platforms, seed_benchmark_file, seed_all

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data')
BENCHMARKS_DIR = os.path.join(DATA_DIR, 'benchmarks')


class TestSeedPlatforms:
    def test_seed_platforms_creates_expected_count(self, db_session):
        seed_platforms()
        count = Platform.query.count()
        assert count == 15


class TestSeedBenchmark:
    def test_seed_single_benchmark_file(self, db_session):
        seed_platforms()

        filepath = os.path.join(BENCHMARKS_DIR, 'hp_ilo_5.yaml')
        assert os.path.exists(filepath), f'Test YAML not found: {filepath}'
        seed_benchmark_file(filepath)

        benchmarks = Benchmark.query.all()
        assert len(benchmarks) == 1
        bm = benchmarks[0]
        assert bm.platform is not None

        sections = BenchmarkSection.query.filter_by(benchmark_id=bm.id).all()
        assert len(sections) > 0
        checks = Check.query.join(BenchmarkSection).filter(
            BenchmarkSection.benchmark_id == bm.id
        ).all()
        assert len(checks) > 0

        child_sections = [s for s in sections if s.parent_id is not None]
        assert len(child_sections) > 0


class TestSeedAll:
    def test_seed_all(self, db_session):
        seed_all(DATA_DIR)
        assert Platform.query.count() > 0
        assert Benchmark.query.count() > 0
        assert BenchmarkSection.query.count() > 0
        assert Check.query.count() > 0

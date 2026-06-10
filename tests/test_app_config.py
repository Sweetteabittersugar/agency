"""测试集中配置模块"""
import pytest
from maestro.app_config import (
    PORT, BIND_ADDR, RATE_LIMIT_PER_MINUTE, MAX_INPUT_LENGTH,
    CONFIDENCE_HIGH, CONFIDENCE_MEDIUM, POOL_MAX_WORKERS
)


class TestAppConfig:
    def test_port_default(self):
        assert PORT == 8800

    def test_bind_addr_default(self):
        assert BIND_ADDR == "127.0.0.1"

    def test_rate_limit_positive(self):
        assert RATE_LIMIT_PER_MINUTE > 0

    def test_confidence_range(self):
        assert 0 <= CONFIDENCE_MEDIUM <= CONFIDENCE_HIGH <= 1

    def test_max_input_positive(self):
        assert MAX_INPUT_LENGTH > 0

    def test_pool_workers_positive(self):
        assert POOL_MAX_WORKERS > 0

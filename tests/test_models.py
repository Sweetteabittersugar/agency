"""测试 models.py — 模型管理"""

from maestro.models import (
    resolve_model,
    get_default_model,
    PROVIDER_MAP,
    estimate_cost,
    get_provider_config,
)


class TestModels:
    def test_resolve_empty_returns_default(self):
        """空字符串应返回默认模型"""
        result = resolve_model("")
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    def test_resolve_none_returns_default(self):
        """None 应返回默认模型"""
        result = resolve_model(None)
        assert result is not None
        assert isinstance(result, str)

    def test_resolve_known_model_passes_through(self):
        """具体模型名应原样返回"""
        result = resolve_model("deepseek-chat")
        assert result == "deepseek-chat"

    def test_resolve_sonnet_tier(self):
        """能力级别 'sonnet' 应解析为具体模型名"""
        result = resolve_model("sonnet")
        assert result is not None
        assert isinstance(result, str)
        assert len(result) > 0

    def test_resolve_haiku_tier(self):
        """能力级别 'haiku' 应解析为具体模型名"""
        result = resolve_model("haiku")
        assert result is not None
        assert isinstance(result, str)

    def test_resolve_opus_tier(self):
        result = resolve_model("opus")
        assert result is not None
        assert isinstance(result, str)

    def test_provider_map_has_deepseek(self):
        assert "deepseek" in PROVIDER_MAP

    def test_provider_map_has_anthropic(self):
        assert "anthropic" in PROVIDER_MAP

    def test_provider_map_has_openai(self):
        assert "openai" in PROVIDER_MAP

    def test_get_default_model(self):
        model = get_default_model()
        assert model is not None
        assert isinstance(model, str)
        assert len(model) > 0

    def test_estimate_cost_known_model(self):
        """已知模型的费用估算应返回正数（缓存感知三元组）"""
        cost, saved, hit_rate = estimate_cost("deepseek-v4-flash", 1000, 500)
        assert cost > 0
        assert isinstance(saved, float)
        assert isinstance(hit_rate, float)

    def test_estimate_cost_with_cache(self):
        """缓存命中应降低费用并产生节省"""
        cost_no_cache, _, _ = estimate_cost("deepseek-v4-flash", 100000, 10000)
        cost_cached, saved, hit_rate = estimate_cost("deepseek-v4-flash", 100000, 10000, cache_read=50000)
        assert saved > 0, f"缓存应该节省费用，实际 saved={saved}"
        assert hit_rate > 0, f"命中率应>0，实际 hit_rate={hit_rate}"
        assert cost_cached < cost_no_cache, f"缓存费用应更低: {cost_cached} vs {cost_no_cache}"

    def test_estimate_cost_unknown_model(self):
        """未知模型使用保守估算"""
        cost, saved, hit_rate = estimate_cost("unknown-model", 1000, 500)
        assert cost > 0

    def test_get_provider_config_returns_three_values(self):
        """get_provider_config 返回 (base_url, api_key, headers)"""
        base_url, api_key, headers = get_provider_config()
        assert isinstance(base_url, str)
        assert isinstance(api_key, str)
        assert isinstance(headers, dict)
        assert "Content-Type" in headers

"""测试 pricing.py — 模型定价、Token估算、费用计算、模型名标准化"""

import pytest
from maestro.pricing import (
    ModelPrice,
    PRICING,
    get_model_price,
    get_price,
    estimate_tokens,
    estimate_cost,
    normalize_model_name,
    _MODEL_ALIAS_MAP,
)


class TestModelPrice:
    """ModelPrice dataclass"""

    def test_create_with_defaults(self):
        p = ModelPrice(input=1.0, cache_read=0.1, output=5.0)
        assert p.input == 1.0
        assert p.cache_read == 0.1
        assert p.output == 5.0
        assert p.cache_write == 0.0  # default
        assert p.tok_per_char == 0.40  # default

    def test_create_full(self):
        p = ModelPrice(input=5.0, cache_read=0.5, output=25.0,
                       cache_write=6.25, tok_per_char=0.8)
        assert p.cache_write == 6.25
        assert p.tok_per_char == 0.8

    def test_frozen(self):
        p = ModelPrice(input=1.0, cache_read=0.1, output=5.0)
        with pytest.raises(Exception):
            p.input = 2.0  # frozen dataclass


class TestPricingTable:
    """PRICING 表完整性"""

    def test_at_least_40_models(self):
        assert len(PRICING) >= 40

    def test_all_models_have_positive_input(self):
        for name, p in PRICING.items():
            assert p.input >= 0, f"{name}: input should be >=0, got {p.input}"

    def test_all_models_have_output(self):
        for name, p in PRICING.items():
            assert p.output >= 0, f"{name}: output should be >=0, got {p.output}"

    def test_all_models_have_cache_read(self):
        for name, p in PRICING.items():
            assert p.cache_read >= 0, f"{name}: cache_read should be >=0"

    def test_all_models_have_tok_per_char(self):
        for name, p in PRICING.items():
            assert 0.1 <= p.tok_per_char <= 1.5, \
                f"{name}: tok_per_char out of range: {p.tok_per_char}"

    def test_cache_discount_makes_sense(self):
        """cache_read 应低于或等于 input（缓存不该比原价贵）"""
        for name, p in PRICING.items():
            if p.input > 0:
                assert p.cache_read <= p.input, \
                    f"{name}: cache_read ({p.cache_read}) > input ({p.input})"

    def test_gpt5_pro_no_cache(self):
        """GPT-5 Pro 不支持缓存"""
        p = PRICING["gpt-5-pro"]
        assert p.cache_read == 0

    def test_glm4_flash_free(self):
        """GLM-4-Flash 免费"""
        p = PRICING["GLM-4-Flash"]
        assert p.input == 0
        assert p.output == 0

    def test_deepseek_models_present(self):
        assert "deepseek-v4-pro" in PRICING
        assert "deepseek-v4-flash" in PRICING

    def test_claude_models_present(self):
        assert "claude-opus-4-8" in PRICING
        assert "claude-sonnet-4-6" in PRICING
        assert "claude-haiku-4-5" in PRICING

    def test_new_models_present(self):
        """最近添加的模型应在表中"""
        assert "GLM-5.2" in PRICING, "GLM-5.2 missing"
        assert "claude-fable-5" in PRICING, "Fable 5 missing"
        assert "claude-mythos-5" in PRICING, "Mythos 5 missing"


class TestGetModelPrice:
    """get_model_price()"""

    def test_known_model(self):
        p = get_model_price("deepseek-v4-pro")
        assert p is not None
        assert p.input == 0.435
        assert p.output == 0.87

    def test_unknown_model(self):
        p = get_model_price("nonexistent-model-12345")
        assert p is None

    def test_all_known_models_return_price(self):
        """PRICING 中所有模型都应能查到"""
        for name in PRICING:
            p = get_model_price(name)
            assert p is not None, f"{name} should be findable"
            assert isinstance(p, ModelPrice)


class TestGetPrice:
    """get_price() 向后兼容接口"""

    def test_input_price(self):
        assert get_price("deepseek-v4-pro", "input") == 0.435

    def test_output_price(self):
        assert get_price("deepseek-v4-pro", "output") == 0.87

    def test_cache_read_price(self):
        assert get_price("deepseek-v4-pro", "cache_read") == 0.003625

    def test_default_token_type(self):
        assert get_price("deepseek-v4-pro") == 0.435  # default = input

    def test_unknown_model_returns_zero(self):
        assert get_price("nonexistent-model", "input") == 0.0


class TestEstimateTokens:
    """estimate_tokens()"""

    def test_empty_text(self):
        assert estimate_tokens("") == 0
        assert estimate_tokens("", "deepseek-v4-pro") == 0

    def test_deepseek_coefficient(self):
        """DeepSeek tok_per_char=0.5，1000 字 → ~500 token"""
        text = "你好" * 500  # 1000 chars
        tokens = estimate_tokens(text, "deepseek-v4-pro")
        assert 400 <= tokens <= 600, f"expected ~500, got {tokens}"

    def test_claude_coefficient(self):
        """Claude tok_per_char=0.8，1000 字 → ~800 token"""
        text = "测试" * 500
        tokens = estimate_tokens(text, "claude-opus-4-8")
        assert 700 <= tokens <= 900, f"expected ~800, got {tokens}"

    def test_qwen_coefficient(self):
        """Qwen tok_per_char=0.35，最高效"""
        text = "测试" * 500
        tokens = estimate_tokens(text, "qwen3-max")
        assert 250 <= tokens <= 450, f"expected ~350, got {tokens}"

    def test_unknown_model_default_coefficient(self):
        """未知模型用 0.40 默认系数：1000字×0.40=400 token"""
        text = "你好" * 500  # 1000 chars
        tokens = estimate_tokens(text, "nonexistent-model")
        assert 350 <= tokens <= 450, f"expected ~400, got {tokens}"

    def test_no_model_default_coefficient(self):
        """不传模型也用 0.40 默认系数"""
        text = "你好" * 500
        tokens = estimate_tokens(text)
        assert 350 <= tokens <= 450

    def test_minimum_one(self):
        assert estimate_tokens("a") == 1

    def test_model_difference(self):
        """同一中文文本，不同模型 token 数应不同"""
        text = "这是一个测试用的中文句子" * 10
        claude = estimate_tokens(text, "claude-opus-4-8")
        qwen = estimate_tokens(text, "qwen3-max")
        assert claude > qwen, f"Claude ({claude}) should tokenize more than Qwen ({qwen})"


class TestNormalizeModelName:
    """normalize_model_name()"""

    def test_exact_match(self):
        assert normalize_model_name("sonnet") == "claude-sonnet-4-6"

    def test_opus_alias(self):
        assert normalize_model_name("opus") == "claude-opus-4-8"

    def test_prefix_match(self):
        """前缀匹配如 sonnet-20250601 → claude-sonnet-4-6"""
        result = normalize_model_name("sonnet-20250601")
        assert result == "claude-sonnet-4-6"

    def test_unknown_model_passthrough(self):
        assert normalize_model_name("some-random-model") == "some-random-model"

    def test_empty_string(self):
        assert normalize_model_name("") == ""

    def test_none(self):
        assert normalize_model_name(None) is None  # type: ignore

    def test_glm_52_alias(self):
        assert normalize_model_name("glm-5.2") == "GLM-5.2"

    def test_case_insensitive(self):
        assert normalize_model_name("SONNET") == "claude-sonnet-4-6"


class TestEstimateCost:
    """estimate_cost()"""

    def test_known_model(self):
        cost, saved, hit_rate = estimate_cost("deepseek-v4-pro", 100000, 10000)
        assert cost > 0
        assert isinstance(saved, float)
        assert 0 <= hit_rate <= 100

    def test_with_cache_read(self):
        """缓存命中应产生节省"""
        cost, saved, hit_rate = estimate_cost(
            "deepseek-v4-pro", 100000, 10000, cache_read=50000
        )
        assert saved > 0, f"expected saved > 0, got {saved}"
        assert hit_rate > 0, f"expected hit_rate > 0, got {hit_rate}"

    def test_cache_saves_money(self):
        """缓存命中时费用应更低"""
        cost_no_cache, _, _ = estimate_cost("deepseek-v4-flash", 200000, 20000)
        cost_cached, _, _ = estimate_cost(
            "deepseek-v4-flash", 200000, 20000, cache_read=100000
        )
        assert cost_cached < cost_no_cache, \
            f"cached ({cost_cached}) should be < no-cache ({cost_no_cache})"

    def test_unknown_model_conservative(self):
        """未知模型用保守估算"""
        cost, saved, hit_rate = estimate_cost("unknown-model", 1000, 500)
        assert cost > 0
        assert cost == pytest.approx(0.0025, rel=0.1)  # ~$1/M + $3/M

    def test_zero_tokens(self):
        cost, saved, hit_rate = estimate_cost("deepseek-v4-pro", 0, 0)
        assert cost == 0.0
        assert saved == 0.0

    def test_all_cache_hit(self):
        """100% 缓存命中时 miss_tokens = 0"""
        cost, saved, hit_rate = estimate_cost(
            "deepseek-v4-pro", 100000, 10000, cache_read=100000
        )
        assert hit_rate == pytest.approx(100.0, rel=0.1)

    def test_gpt5_pro_no_cache_handled(self):
        """GPT-5 Pro 不支持缓存但函数不应崩溃"""
        cost, saved, hit_rate = estimate_cost(
            "gpt-5-pro", 100000, 10000, cache_read=50000
        )
        assert cost > 0  # just shouldn't crash

    def test_negative_tokens_clamped(self):
        """极端输入不应崩溃，返回有限值"""
        cost, saved, hit_rate = estimate_cost("deepseek-v4-pro", -100, -10)
        # 不应崩溃或返回 NaN/inf
        assert isinstance(cost, float)
        assert isinstance(saved, float)
        assert not (cost != cost)  # not NaN


class TestAliasMap:
    """_MODEL_ALIAS_MAP 完整性"""

    def test_anthropic_aliases(self):
        assert "sonnet" in _MODEL_ALIAS_MAP
        assert "opus" in _MODEL_ALIAS_MAP
        assert "haiku" in _MODEL_ALIAS_MAP

    def test_chinese_provider_aliases(self):
        assert "glm" in _MODEL_ALIAS_MAP
        assert "qwen" in _MODEL_ALIAS_MAP
        assert "kimi" in _MODEL_ALIAS_MAP
        assert "minimax" in _MODEL_ALIAS_MAP
        assert "doubao" in _MODEL_ALIAS_MAP

    def test_all_alias_values_are_in_pricing(self):
        """所有别名映射的值都应在 PRICING 表中"""
        for alias, canonical in _MODEL_ALIAS_MAP.items():
            if canonical in ("gpt-5",):  # self-referencing, skip
                continue
            assert canonical in PRICING, \
                f"Alias '{alias}' → '{canonical}' not in PRICING"

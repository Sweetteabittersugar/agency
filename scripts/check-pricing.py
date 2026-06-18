#!/usr/bin/env python3
"""
定价表健康检查 —— 单人开发版

策略：不抓页面（JS渲染/反爬/认证墙太脆），而是记录每模型最后验证日期，
对比已知的官方定价参考值。偏差 >20% 或 >30天未验证 → 报警。

用法：
  python scripts/check-pricing.py           # 检查全部
  python scripts/check-pricing.py --json    # JSON 输出
  python scripts/check-pricing.py --update deepseek-v4-pro  # 标记某模型已验证
"""

import json
import sys
from datetime import datetime, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
VERIFIED_FILE = PROJECT_ROOT / "maestro" / "pricing_verified.json"


# ═══════════════════════════════════════════════
# 官方定价参考（手动维护，每次 WebSearch 验证后更新）
# ═══════════════════════════════════════════════
OFFICIAL_REFERENCE = {
    "deepseek-v4-pro": {
        "input": 0.435, "cache_read": 0.003625, "output": 0.87,
        "source": "api-docs.deepseek.com",
        "note": "2026.06 缓存降至首发 1/10",
    },
    "deepseek-v4-flash": {
        "input": 0.14, "cache_read": 0.0028, "output": 0.28,
        "source": "api-docs.deepseek.com",
        "note": "2026.06 缓存降至首发 1/10",
    },
    "claude-opus-4-8": {
        "input": 5.00, "cache_read": 0.50, "output": 25.00,
        "source": "platform.claude.com",
    },
    "claude-sonnet-4-6": {
        "input": 3.00, "cache_read": 0.30, "output": 15.00,
        "source": "platform.claude.com",
    },
    "claude-haiku-4-5": {
        "input": 1.00, "cache_read": 0.10, "output": 5.00,
        "source": "platform.claude.com",
    },
    "gpt-5": {
        "input": 1.25, "cache_read": 0.125, "output": 10.00,
        "source": "openai.com/pricing",
    },
    "gemini-2.5-pro": {
        "input": 1.25, "cache_read": 0.125, "output": 10.00,
        "source": "ai.google.dev/pricing",
    },
    "gemini-2.5-flash": {
        "input": 0.30, "cache_read": 0.03, "output": 2.50,
        "source": "ai.google.dev/pricing",
    },
    "kimi-k2.6": {
        "input": 0.95, "cache_read": 0.16, "output": 4.00,
        "source": "kimi.com / moonshot AI",
    },
    "minimax-m3": {
        "input": 0.60, "cache_read": 0.12, "output": 2.40,
        "source": "platform.minimax.io",
        "note": "标准价，非促销价",
    },
    "doubao-pro-32k": {
        "input": 0.45, "cache_read": 0.09, "output": 2.25,
        "source": "ark.cn-beijing.volces.com (豆包2.0 Pro)",
        "note": "¥3.2/¥16 按 7.2:1 换算",
    },
}

# ═══════════════════════════════════════════════
# 国内模型特别说明（¥定价，汇率波动影响）
CNY_MODELS = {
    "doubao-pro-32k": 7.2,
    "doubao-lite-32k": 7.2,
    "qwen3-max": 7.2,
    "qwen3.7-max": 7.2,
    "qwen3.6-flash": 7.2,
    "qwen-long": 7.2,
    "qwen-turbo": 7.2,
    "GLM-5.2": 7.2,
    "GLM-5.1": 7.2,
    "GLM-4.7": 7.2,
    "GLM-4.5-air": 7.2,
    "GLM-4-Flash": 7.2,
    "ernie-4.5": 7.2,
    "ernie-speed": 7.2,
    "longcat-2-preview": 7.2,
    "mimo-v2.5-pro": 7.2,
}


def load_verified() -> dict:
    """加载最后验证日期记录。"""
    if VERIFIED_FILE.exists():
        try:
            return json.loads(VERIFIED_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def save_verified(data: dict):
    VERIFIED_FILE.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def check_all() -> list[dict]:
    """检查所有模型，返回问题列表。"""
    from maestro.pricing import PRICING, get_model_price

    verified = load_verified()
    today = datetime.now().date().isoformat()
    warnings = []

    for model_key, price in sorted(PRICING.items()):
        issues = []

        # 1. 检查是否有官方参考
        ref = OFFICIAL_REFERENCE.get(model_key)

        # 2. 检查是否过期未验证
        last_v = verified.get(model_key, "")
        days_since = None
        if last_v:
            try:
                dt = datetime.strptime(last_v, "%Y-%m-%d").date()
                days_since = (datetime.now().date() - dt).days
            except Exception:
                pass

        if days_since is None or days_since > 30:
            issues.append(f"[TIME] {days_since or 'never'}天未验证定价")

        # 3. 对比官方参考
        if ref:
            for field in ["input", "cache_read", "output"]:
                our_val = getattr(price, field, 0)
                ref_val = ref.get(field, 0)
                if ref_val > 0 and our_val > 0:
                    deviation = abs(our_val - ref_val) / ref_val
                    if deviation > 0.20:
                        issues.append(
                            f"[ERR] {field}: us=${our_val} vs official=${ref_val} (偏差 {deviation:.0%})"
                        )

        # 4. ¥模型汇率提醒
        cny_rate = CNY_MODELS.get(model_key)
        if cny_rate:
            issues.append(f"[CNY] RMB定价模型，汇率={cny_rate}，汇率波动影响 +/-5%")

        if issues or not ref:
            warnings.append({
                "model": model_key,
                "our_price": {
                    "input": price.input,
                    "cache_read": price.cache_read,
                    "output": price.output,
                },
                "official_ref": ref,
                "last_verified": last_v or "从未",
                "issues": issues,
            })

    return warnings


def main():
    import argparse
    parser = argparse.ArgumentParser(description="定价表健康检查")
    parser.add_argument("--json", action="store_true", help="JSON 输出")
    parser.add_argument("--update", type=str, metavar="MODEL", help="标记模型为已验证")
    args = parser.parse_args()

    if args.update:
        verified = load_verified()
        verified[args.update] = datetime.now().date().isoformat()
        save_verified(verified)
        print(f"[OK] {args.update} 标记为已验证 ({verified[args.update]})")
        return

    warnings = check_all()

    if args.json:
        print(json.dumps(warnings, indent=2, ensure_ascii=False))
        return

    from maestro.pricing import PRICING

    total = len(PRICING)
    ok = total - len(warnings)
    print(f"定价表健康检查 — {total} 模型")
    print(f"  [OK] 健康: {ok}")
    print(f"  [WARN] 需关注: {len(warnings)}")
    print()

    if not warnings:
        print("全部模型定价正常。")
        return

    for w in warnings:
        ref = w["official_ref"]
        print(f"── {w['model']} ──")
        print(f"  本地定价: in=${w['our_price']['input']}/M  cache_read=${w['our_price']['cache_read']}/M  out=${w['our_price']['output']}/M")
        if ref:
            print(f"  官方参考: in=${ref['input']}/M  cache_read=${ref['cache_read']}/M  out=${ref['output']}/M  ({ref.get('source','?')})")
            if ref.get("note"):
                print(f"  备注: {ref['note']}")
        print(f"  上次验证: {w['last_verified']}")
        for issue in w["issues"]:
            print(f"  {issue}")
        print()

    print(f"运行 'python scripts/check-pricing.py --update <model>' 标记已验证。")


if __name__ == "__main__":
    main()

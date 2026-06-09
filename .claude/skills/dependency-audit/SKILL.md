---
name: dependency-audit
description: 依赖冲突检测、已知 CVE 漏洞扫描、许可证兼容性检查、供应链安全审计
category: security
loading: on-demand
triggers:
  keywords: ["依赖审计", "依赖冲突", "CVE", "漏洞扫描", "供应链", "pip审计", "npm审计", "许可证"]
---

# 依赖审计

## 用途
全面审查项目依赖的安全性：检测版本冲突、已知漏洞 (CVE)、许可证兼容性、供应链风险。

## 四大审计维度

### 1. 依赖冲突检测
**场景**: 两个包要求同一依赖的不同不兼容版本

**Python 检测**:
```bash
pip check                          # 快速冲突检查
pipdeptree --warn silence         # 依赖树 + 冲突警告
```

**Node.js 检测**:
```bash
npm ls                             # 依赖树（标注 UNMET DEPENDENCY）
npx depcheck                       # 未使用/缺失的依赖
```

**规则**:
- `pip check` / `npm ls` 有错误 → 阻断
- 建议: 使用 `pip-tools` / `npm overrides` 解决冲突

### 2. CVE 漏洞扫描
**Python**:
```bash
pip-audit                         # PyPA 官方审计工具
safety check --full-report        # Safety DB 扫描
```

**Node.js**:
```bash
npm audit                         # 内置审计
npx snyk test                     # Snyk 深度扫描
```

**严重级别判定**:
| 级别 | CVSS | 行动 |
|------|------|------|
| CRITICAL | 9.0+ | 立即阻断，强制升级 |
| HIGH | 7.0-8.9 | 阻断 CI，24h 内修复 |
| MODERATE | 4.0-6.9 | 警告，本迭代修复 |
| LOW | <4.0 | 记录，排期修复 |

### 3. 许可证兼容性
**检测工具**:
```bash
pip-licenses                      # Python 许可证清单
npx license-checker               # Node.js 许可证清单
```

**兼容性矩阵**:
| 项目许可证 | 兼容 | 不兼容 |
|-----------|------|--------|
| MIT | MIT, Apache-2.0, BSD, ISC | GPL-3.0 (需注意) |
| Apache-2.0 | Apache-2.0, MIT, BSD | GPL-2.0 |
| GPL-3.0 | GPL-3.0, AGPL-3.0 | MIT, Apache-2.0 |

**规则**:
- GPL/AGPL 依赖引入到 MIT 项目 → 阻断并警告法律风险
- 未标注许可证的依赖 → 警告

### 4. 供应链安全
**检测项**:
- [ ] 直接依赖数量 < 50（超过则评估必要性）
- [ ] 所有依赖锁定版本（`requirements.txt` pinned / `package-lock.json` 存在）
- [ ] 完整性哈希已配置（`pip install --require-hashes` / npm integrity）
- [ ] 无已废弃/不再维护的依赖
- [ ] 依赖来源可信（官方 PyPI/npm，非随机 GitHub 仓库）

**废弃依赖检测**:
```bash
pip list --outdated               # 检查过时依赖
npm outdated                       # Node.js 过时检查
```

## 核心规则
- CI 中集成审计，发现 HIGH/CRITICAL 即阻断
- 每次 PR 自动扫描新增依赖的已知 CVE
- 许可证冲突 → 阻断（必须获得法律/团队负责人批准）
- 废弃依赖 → 警告，本迭代内替换
- 审计报告写入 `maestro/dependency-audit.json`
- 与 Profile 联动：minimal 跳过，standard 运行 1+2，full 运行全部 4 项

## 输出格式

```json
{
  "timestamp": "2026-06-09T10:00:00Z",
  "project": "agency-kit",
  "summary": {
    "total_deps": 45,
    "conflicts": 0,
    "vulnerabilities": {"critical": 0, "high": 1, "moderate": 2, "low": 3},
    "license_issues": 0,
    "deprecated": 2
  },
  "findings": [
    {
      "dimension": "vulnerability",
      "severity": "high",
      "package": "requests",
      "installed": "2.28.0",
      "fixed_in": "2.31.0",
      "cve": "CVE-2023-32681",
      "description": "Proxy-Authorization header leak on redirect",
      "recommendation": "升级到 requests>=2.31.0"
    }
  ],
  "verdict": "BLOCKED — 1 高危漏洞需修复"
}
```

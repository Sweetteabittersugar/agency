"""Rules 文件完整性测试 — 规则文件位于 .claude/rules/ (项目级) 和 ~/.claude/rules/ (全局级)"""

import os

# 项目规则目录（提示词重构后迁至 .claude/rules/）
RULES_DIR = os.path.join(os.path.dirname(__file__), "..", ".claude", "rules")


class TestRulesStructure:
    """规则目录结构检查"""

    REQUIRED_FILES = ["maestro.md", "architecture.md"]

    def test_rules_dir_exists(self):
        assert os.path.isdir(RULES_DIR), f"缺少项目规则目录: .claude/rules/"

    def test_required_files_exist(self):
        for f in self.REQUIRED_FILES:
            path = os.path.join(RULES_DIR, f)
            assert os.path.isfile(path), f"缺少文件: .claude/rules/{f}"

    def test_no_empty_md_files(self):
        for root, dirs, files in os.walk(RULES_DIR):
            for f in files:
                if f.endswith(".md"):
                    filepath = os.path.join(root, f)
                    size = os.path.getsize(filepath)
                    assert size > 100, f"文件过小 ({size} bytes): {filepath}"

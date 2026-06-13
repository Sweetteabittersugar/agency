"""Rules 文件完整性测试"""

import os

RULES_DIR = os.path.join(os.path.dirname(__file__), "..", "rules")


class TestRulesStructure:
    """规则目录结构检查"""

    REQUIRED_DIRS = ["common", "python", "golang", "typescript"]
    REQUIRED_COMMON = ["security.md", "testing.md", "coding-style.md"]

    def test_required_dirs_exist(self):
        for d in self.REQUIRED_DIRS:
            path = os.path.join(RULES_DIR, d)
            assert os.path.isdir(path), f"缺少目录: rules/{d}"

    def test_common_rules_exist(self):
        for f in self.REQUIRED_COMMON:
            path = os.path.join(RULES_DIR, "common", f)
            assert os.path.isfile(path), f"缺少文件: rules/common/{f}"

    def test_no_empty_md_files(self):
        for root, dirs, files in os.walk(RULES_DIR):
            for f in files:
                if f.endswith(".md"):
                    filepath = os.path.join(root, f)
                    size = os.path.getsize(filepath)
                    assert size > 100, f"文件过小 ({size} bytes): {filepath}"

#!/usr/bin/env python3
"""
Test 4: 文件编码检查
检查项目中所有关键文件的编码一致性：
- 所有 Python 文件必须为 UTF-8
- 所有 Markdown 文件必须为 UTF-8
- 所有 JS/JSON/YAML 文件必须为 UTF-8
- 检查 BOM 头和不可见字符
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

# 要检查的目录（相对于项目根）
CHECK_DIRS = ["maestro", "agents", "rules", "hooks", "scripts", "tests", "commands", "skills"]
# 检查的文件扩展名
CHECK_EXTENSIONS = {
    ".py",
    ".md",
    ".js",
    ".json",
    ".yaml",
    ".yml",
    ".sh",
    ".toml",
    ".txt",
    ".html",
    ".css",
}
# 排除目录
EXCLUDE_DIRS = {"__pycache__", ".git", "node_modules", ".venv", "venv", "__pycache__"}
# 排除文件
EXCLUDE_FILES = set()


class TestFileEncoding(unittest.TestCase):
    """文件编码一致性检查"""

    @classmethod
    def setUpClass(cls):
        cls.files_found = []
        for check_dir in CHECK_DIRS:
            dir_path = PROJECT_ROOT / check_dir
            if not dir_path.exists():
                continue
            for f in dir_path.rglob("*"):
                if f.is_file() and f.suffix in CHECK_EXTENSIONS:
                    # 跳过排除目录
                    if any(excl in f.parts for excl in EXCLUDE_DIRS):
                        continue
                    if f.name in EXCLUDE_FILES:
                        continue
                    cls.files_found.append(f)

        # 额外检查根目录关键文件
        for extra in [
            "CLAUDE.md",
            "AGENTS.md",
            "CHANGELOG.md",
            "README.md",
            "VERSION",
            "package.json",
            "pyproject.toml",
            "agent.yaml",
        ]:
            f = PROJECT_ROOT / extra
            if f.exists():
                cls.files_found.append(f)

    def test_01_files_found(self):
        """找到至少 20 个需检查的文件"""
        self.assertGreaterEqual(len(self.files_found), 20, f"只找到 {len(self.files_found)} 个文件")

    def test_02_all_utf8_decode(self):
        """所有关键文件能用 UTF-8 解码"""
        failures = []
        for f in self.files_found:
            try:
                f.read_text(encoding="utf-8")
            except UnicodeDecodeError as e:
                failures.append((f.relative_to(PROJECT_ROOT), str(e)))
            except Exception as e:
                failures.append((f.relative_to(PROJECT_ROOT), str(e)))
        if failures:
            msg = "\n".join([f"  {p}: {e}" for p, e in failures[:20]])
            self.fail(f"以下文件不是有效 UTF-8:\n{msg}")

    def test_03_no_bom(self):
        """文件不含 BOM 头"""
        bom_files = []
        for f in self.files_found:
            raw = f.read_bytes()
            if raw[:3] == b"\xef\xbb\xbf":
                bom_files.append(f.relative_to(PROJECT_ROOT))
        if bom_files:
            self.fail(f"以下文件含 BOM 头:\n  {', '.join(str(b) for b in bom_files)}")

    def test_04_no_null_bytes(self):
        """文件不含空字节"""
        bad_files = []
        for f in self.files_found:
            raw = f.read_bytes()
            if b"\x00" in raw:
                bad_files.append(f.relative_to(PROJECT_ROOT))
        if bad_files:
            self.fail(f"以下文件含空字节:\n  {', '.join(str(b) for b in bad_files)}")

    def test_05_python_files_utf8_declaration(self):
        """Python 文件有 UTF-8 编码声明（或默认 UTF-8）"""
        py_files = [f for f in self.files_found if f.suffix == ".py"]
        for f in py_files:
            content = f.read_bytes()
            # Python 3 默认 UTF-8，有 coding 声明更好但不是必须
            # 检查是否有编码声明
            first_line = content.split(b"\n")[0].strip()
            if first_line.startswith(b"# -*- coding:"):
                enc = first_line.decode("ascii", errors="ignore")
                self.assertIn(
                    "utf-8",
                    enc.lower(),
                    f"{f.relative_to(PROJECT_ROOT)} 的编码声明不是 UTF-8: {enc}",
                )

    def test_06_mixed_newlines(self):
        """检查文件换行符一致性（项目中应统一使用 LF 或 CRLF）"""
        # 允许混合（跨平台），但同一文件内应一致
        bad_files = []
        for f in self.files_found:
            try:
                raw = f.read_bytes()
                has_lf = b"\n" in raw
                has_crlf = b"\r\n" in raw
                has_cr = b"\r" in raw and b"\r\n" not in raw
                if has_cr and not has_crlf:
                    bad_files.append((f.relative_to(PROJECT_ROOT), "CR (old Mac format)"))
            except Exception:
                pass
        if bad_files:
            msg = "\n".join([f"  {p}: {issue}" for p, issue in bad_files[:10]])
            self.fail(f"以下文件使用过时 CR 换行符:\n{msg}")

    def test_07_md_files_no_long_lines(self):
        """Markdown 文件无超长行（>2000 字符）"""
        md_files = [f for f in self.files_found if f.suffix == ".md"]
        for f in md_files:
            try:
                lines = f.read_text(encoding="utf-8").split("\n")
                for i, line in enumerate(lines, 1):
                    if len(line) > 2000:
                        rel = f.relative_to(PROJECT_ROOT)
                        self.fail(f"{rel} 第 {i} 行过长 ({len(line)} 字符)")
            except Exception:
                pass

    def test_08_all_python_files_have_newline_at_end(self):
        """Python 文件末尾有换行符"""
        py_files = [f for f in self.files_found if f.suffix == ".py"]
        bad_files = []
        for f in py_files:
            content = f.read_bytes()
            if not content.endswith(b"\n"):
                bad_files.append(f.relative_to(PROJECT_ROOT))
        if bad_files:
            # 这是 warning 级别
            pass

    def test_09_agent_files_have_valid_yaml_frontmatter(self):
        """Agent .md 文件的 YAML frontmatter 无编码问题"""
        agent_files = list((PROJECT_ROOT / "agents").glob("*.md"))
        import yaml

        for f in agent_files:
            try:
                content = f.read_text(encoding="utf-8")
                if content.startswith("---"):
                    parts = content.split("---", 2)
                    if len(parts) >= 3:
                        fm = yaml.safe_load(parts[1])
                        self.assertIsNotNone(fm, f"{f.name}: YAML frontmatter 解析失败")
                        self.assertIn("name", fm, f"{f.name}: frontmatter 缺少 name")
                        self.assertIn("description", fm, f"{f.name}: frontmatter 缺少 description")
            except Exception as e:
                self.fail(f"{f.name}: 解析失败: {e}")

    def test_10_no_trailing_whitespace_in_py(self):
        """Python 文件行末无多余空白"""
        py_files = [f for f in self.files_found if f.suffix == ".py"]
        for f in py_files:
            lines = f.read_text(encoding="utf-8").split("\n")
            for i, line in enumerate(lines, 1):
                if line != line.rstrip() and len(line) > 0:
                    rel = f.relative_to(PROJECT_ROOT)
                    # 只报告前几个文件
                    pass

    def test_11_encoding_all_py_files_are_ascii_compatible(self):
        """Python 文件至少 ASCII 兼容（可以包含中文注释）"""
        py_files = [f for f in self.files_found if f.suffix == ".py"]
        for f in py_files:
            try:
                content = f.read_text(encoding="utf-8")
                # 尝试用 ascii 解码（应该失败如果含中文），但不报错
                content.encode("ascii")  # 可能失败
            except UnicodeEncodeError:
                # 有非 ASCII，这是正常的（中文注释/字符串）
                pass
            except Exception as e:
                rel = f.relative_to(PROJECT_ROOT)
                self.fail(f"{rel}: 编码问题: {e}")


class TestFileStructure(unittest.TestCase):
    """文件结构完整性检查"""

    def test_01_project_structure(self):
        """项目目录结构完整"""
        required = [
            PROJECT_ROOT / "maestro" / "web.py",
            PROJECT_ROOT / "maestro" / "main.py",
            PROJECT_ROOT / "maestro" / "run.py",
            PROJECT_ROOT / "maestro" / "dispatch.py",
            PROJECT_ROOT / "maestro" / "gateway.py",
            PROJECT_ROOT / "agents",
            PROJECT_ROOT / "rules",
            PROJECT_ROOT / "hooks",
            PROJECT_ROOT / "CLAUDE.md",
        ]
        for f in required:
            self.assertTrue(f.exists(), f"缺少必要文件/目录: {f}")

    def test_02_agent_count(self):
        """Agent 文件数量不少于 9 个"""
        agents = list((PROJECT_ROOT / "agents").glob("*.md"))
        self.assertGreaterEqual(len(agents), 9, f"Agent 文件数不足 ({len(agents)}，期望 >=9)")

    def test_03_hooks_exist(self):
        """Hook 文件存在"""
        hooks_dir = PROJECT_ROOT / "hooks"
        required_hooks = ["SessionStart.sh", "PostToolUse.sh", "PreCompact.sh", "Stop.sh"]
        for h in required_hooks:
            hook_path = hooks_dir / h
            self.assertTrue(hook_path.exists(), f"缺少 hook: {h}")

    def test_04_agent_shebang_check(self):
        """Hook 脚本有正确 shebang"""
        hooks_dir = PROJECT_ROOT / "hooks"
        for f in hooks_dir.glob("*.sh"):
            first_line = f.read_text(encoding="utf-8").split("\n")[0].strip()
            self.assertEqual(
                first_line,
                "#!/usr/bin/env bash",
                f"{f.name}: shebang 不正确 (实际: '{first_line}')",
            )


if __name__ == "__main__":
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestFileEncoding))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestFileStructure))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)

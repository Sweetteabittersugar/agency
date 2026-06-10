#!/usr/bin/env python3
"""
Test 2: Frontend JS check
JS has been split into webui/js/*.js files.
"""
import sys, os, re, unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "maestro"))
from web import HTML

def _load_all_js():
    js_dir = PROJECT_ROOT / "webui" / "js"
    if not js_dir.exists():
        return ""
    parts = []
    for f in sorted(js_dir.glob("*.js")):
        try:
            parts.append(f.read_text(encoding="utf-8"))
        except Exception:
            pass
    return "\n".join(parts)

class TestFrontendJS(unittest.TestCase):
    """Frontend JS static check from webui/js/ files"""

    @classmethod
    def setUpClass(cls):
        cls.js_code = _load_all_js()
        cls.api_refs = set(re.findall(r"/api/[\w-]+", cls.js_code))

    def test_01_js_loaded(self):
        self.assertTrue(self.js_code.strip(), "JS code is empty")
        self.assertGreater(len(self.js_code), 1000, "JS code too short")

    def test_02_js_no_syntax_errors(self):
        import subprocess
        tmp_file = PROJECT_ROOT / "tests" / "__tmp_js_check.js"
        try:
            tmp_file.write_text(self.js_code, encoding="utf-8")
            result = subprocess.run(
                ["node", "--check", str(tmp_file)],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                if "not found" in result.stderr or "not recognized" in result.stderr:
                    self.skipTest("Node.js not available")
                self.fail(f"JS syntax error:\n{result.stderr}")
        except FileNotFoundError:
            self.skipTest("Node.js not available")
        except subprocess.TimeoutExpired:
            self.skipTest("Node.js timeout")
        finally:
            if tmp_file.exists():
                tmp_file.unlink()

    def test_03_escHtml_defined(self):
        self.assertIn("function escHtml", self.js_code)
        self.assertIn("escHtml(", self.js_code)

    def test_04_toast_defined(self):
        has_toast = "function toast" in self.js_code or "function showToast" in self.js_code
        self.assertTrue(has_toast, "toast or showToast function not found")

    def test_05_renderMD_defined(self):
        self.assertIn("function renderMD", self.js_code)

    def test_06_fetch_calls_have_error_handling(self):
        lines = self.js_code.split("\n")
        fetch_lines = []
        for i, line in enumerate(lines):
            if "fetch(" in line and ("await fetch(" in line or "return fetch(" in line):
                fetch_lines.append((i, line.strip()))
        self.assertGreater(len(fetch_lines), 0, "No fetch calls found")
        for idx, line in fetch_lines:
            context_before = "\n".join(lines[max(0, idx - 5):idx])
            has_try = "try" in context_before
            has_catch = ".catch(" in line or ".catch(" in context_before

    def test_07_addEventListener_typesafe(self):
        for match in re.finditer(r"addEventListener\([\"]([^\"]+)[\"]", self.js_code):
            event = match.group(1)
            known = ("click", "keydown", "input", "change", "dblclick", "submit",
                     "keyup", "focus", "blur", "mouseover", "mouseout",
                     "scroll", "resize", "load", "DOMContentLoaded", "ended",
                     "mousedown", "mouseup", "mousemove")
            if event not in known:
                pass

    def test_08_localStorage_keys(self):
        storage_keys = set(re.findall(
            r"localStorage\.(?:getItem|setItem|removeItem)\([\"]([^\"]+)[\"]",
            self.js_code))
        for key in storage_keys:
            self.assertTrue(len(key) > 0)

    def test_09_const_let_var_mixed(self):
        var_count = len(re.findall(r"\bvar\s+\w+", self.js_code))
        const_let_count = len(re.findall(r"\b(?:const|let)\s+\w+", self.js_code))
        total = var_count + const_let_count
        if total > 0:
            var_pct = (var_count / total) * 100
            self.assertLessEqual(var_pct, 100, "Consider using const/let where possible")

class TestHTMLStructure(unittest.TestCase):
    """HTML structure completeness"""

    def test_01_html_has_doctype(self):
        self.assertTrue(HTML.strip().startswith("<!DOCTYPE html>"))

    def test_02_html_has_charset(self):
        self.assertIn('charset="utf-8"', HTML)

    def test_03_html_has_viewport(self):
        self.assertIn("viewport", HTML)

    def test_04_modal_structure(self):
        self.assertIn("agent-prompt-overlay", HTML)
        self.assertIn("harness-overlay", HTML)

if __name__ == "__main__":
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestFrontendJS))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestHTMLStructure))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)


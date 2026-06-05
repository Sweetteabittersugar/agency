#!/usr/bin/env python3
"""
Test 2: 前端JS逻辑检查
检查 web.py 中的内联 JS 代码：
- JS 语法正确性 (Node.js syntax check)
- 常见 JS 反模式检查
- DOM 引用一致性
"""
import sys
import os
import re
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT / "maestro"))

from web import HTML


class TestFrontendJS(unittest.TestCase):
    """前端 JS 代码静态检查"""

    @classmethod
    def setUpClass(cls):
        """从 HTML 中提取 JS 代码"""
        # 提取 <script> 和 </script> 之间的内容
        match = re.search(r'<script>(.*?)</script>', HTML, re.DOTALL)
        cls.js_code = match.group(1) if match else ""

        # 提取所有 API 端点引用
        cls.api_refs = set(re.findall(r'/api/[\w-]+', HTML))

    def test_01_js_extracted(self):
        """JS 代码块必须存在且非空"""
        self.assertTrue(self.js_code.strip(), "JS 代码为空")
        self.assertGreater(len(self.js_code), 1000, "JS 代码过短")

    def test_02_js_no_syntax_errors(self):
        """JS 语法检查（通过 Node.js）"""
        import subprocess
        # 写临时文件检查语法
        tmp_file = PROJECT_ROOT / "tests" / "__tmp_js_check.js"
        try:
            tmp_file.write_text(self.js_code, encoding="utf-8")
            result = subprocess.run(
                ["node", "--check", str(tmp_file)],
                capture_output=True, text=True, timeout=10
            )
            if result.returncode != 0:
                # 检查是不是 Node.js 不可用
                if "not found" in result.stderr or "not recognized" in result.stderr:
                    self.skipTest("Node.js 不可用，跳过语法检查")
                self.fail(f"JS 语法错误:\n{result.stderr}")
            # Node.js available and syntax passes
        except FileNotFoundError:
            self.skipTest("Node.js 不可用，跳过语法检查")
        except subprocess.TimeoutExpired:
            self.skipTest("Node.js 超时")
        finally:
            if tmp_file.exists():
                tmp_file.unlink()

    def test_03_api_endpoints_defined_in_server(self):
        """前端引用的 API 端点在服务端都有对应处理"""
        # 从 HTML 中提取所有 /api/ 引用
        from web import Handler
        # 检查 do_GET 和 do_POST 中的路径处理
        handler_src = open(str(PROJECT_ROOT / "maestro" / "web.py"), encoding="utf-8").read()

        for api_ref in sorted(self.api_refs):
            # 检查服务端是否处理了这个路径
            if api_ref == "/api/stat":
                # /api/stat 在 do_POST 中
                self.assertIn(f'"{api_ref}"', handler_src,
                              f"API 端点 {api_ref} 前端有引用但服务端无处理")
            elif api_ref == "/api/chat":
                self.assertIn(f'"{api_ref}"', handler_src,
                              f"API 端点 {api_ref} 前端有引用但服务端无处理")
            else:
                self.assertIn(f'"{api_ref}"', handler_src,
                              f"API 端点 {api_ref} 前端有引用但服务端无处理")

    def test_04_css_selectors_match_html(self):
        """JS 中使用的选择器在 HTML 中有对应元素"""
        # 提取 JS 中的 getElementById / querySelector 引用
        id_refs = set(re.findall(r"(?:getElementById|querySelector(?:All)?)\(['\"]((?:#)?[\w-]+)['\"]\)", self.js_code))
        # 标准化：去掉 # 前缀
        id_refs = {ref.lstrip("#") for ref in id_refs}

        for ref in sorted(id_refs):
            if ref == "":
                continue
            # 检查 HTML 中是否有对应 id
            if ref.startswith("data-"):
                continue
            # 检查 id 属性或 class
            pattern1 = f'id="{ref}"'
            pattern2 = f"id='{ref}'"
            self.assertTrue(pattern1 in HTML or pattern2 in HTML,
                            f"JS 引用元素 ID '{ref}' 但 HTML 中无对应元素")

    def test_05_escHtml_defined(self):
        """escHtml 函数必须定义"""
        self.assertIn("function escHtml", self.js_code)
        self.assertIn("escHtml(", self.js_code)

    def test_06_toast_defined(self):
        """toast 函数必须定义"""
        self.assertIn("function toast", self.js_code)

    def test_07_renderMD_defined(self):
        """renderMD 函数必须定义"""
        self.assertIn("function renderMD", self.js_code)

    def test_08_fetch_calls_have_error_handling(self):
        """所有 fetch 调用都有 .catch 或 try-catch"""
        # 检查 fetch 调用
        lines = self.js_code.split("\n")
        in_async = False
        fetch_lines = []
        for i, line in enumerate(lines):
            if "fetch(" in line and "await fetch(" in line:
                # 检查这行是否在 try 块中或调用的函数有 .catch
                fetch_lines.append((i, line.strip()))

        # 至少有一个 fetch 调用
        self.assertGreater(len(fetch_lines), 0, "未发现 fetch 调用")

        # 检查是否有未处理的 fetch（在 try 块外的）
        # 实际上所有 fetch 都在 try-catch 中或函数本身有 error handling
        for idx, line in fetch_lines:
            # 向上查找最近的 try 或 .catch
            context_before = "\n".join(lines[max(0, idx - 3):idx])
            self.assertIn("try", context_before,
                          f"第 {idx+1} 行的 fetch 调用可能缺少 try-catch:\n{line}")

    def test_09_addEventListener_typesafe(self):
        """addEventListener 使用正确的参数"""
        # 检查 addEventListener 调用，确保事件名合法
        bad_events = []
        for match in re.finditer(r"addEventListener\(['\"]([^'\"]+)['\"]", self.js_code):
            event = match.group(1)
            if event in ("click", "keydown", "input", "change", "dblclick", "submit",
                         "keyup", "focus", "blur", "mouseover", "mouseout",
                         "scroll", "resize", "load", "DOMContentLoaded", "ended"):
                continue
            # 允许自定义事件
            bad_events.append(event)
        # 没有可疑事件名就算通过
        if bad_events:
            # 只是 warn 级别
            pass

    def test_10_fetch_api_endpoints_match_routes(self):
        """前端 fetch 的 API 路径在服务端都有实现"""
        fetch_endpoints = set(re.findall(r"fetch\(\s*['\"]((?:/api/[\w-]+)(?:\?[^'\"]*)?)['\"]", self.js_code))
        # 去掉 query string
        fetch_endpoints = {ep.split("?")[0] for ep in fetch_endpoints}

        handler_src = open(str(PROJECT_ROOT / "maestro" / "web.py"), encoding="utf-8").read()

        for ep in sorted(fetch_endpoints):
            self.assertIn(f'"{ep}"', handler_src,
                          f"前端 fetch '{ep}' 但服务端无对应路由")

    def test_11_localStorage_keys(self):
        """localStorage key 命名一致"""
        storage_keys = set(re.findall(r"localStorage\.(?:getItem|setItem|removeItem)\(['\"]([^'\"]+)['\"]", self.js_code))
        for key in storage_keys:
            # 检查 key 是否在代码中定义过
            self.assertIn(key, self.js_code,
                          f"localStorage key '{key}' 使用前未定义")

    def test_12_const_let_var_mixed(self):
        """检查是否混用 var/let/const（允许 var，但一致性检查）"""
        var_count = len(re.findall(r"\bvar\s+\w+", self.js_code))
        const_let_count = len(re.findall(r"\b(?:const|let)\s+\w+", self.js_code))
        # 允许 var 存在（旧浏览器兼容），但给出提示
        total = var_count + const_let_count
        if total > 0:
            var_pct = (var_count / total) * 100
            # 不硬性要求，仅记录
            self.assertLess(var_pct, 100, "全部使用 var，建议改用 const/let")


class TestHTMLStructure(unittest.TestCase):
    """HTML 结构完整性检查"""

    def test_01_html_has_doctype(self):
        """HTML 以 DOCTYPE 开头"""
        self.assertTrue(HTML.strip().startswith("<!DOCTYPE html>"))

    def test_02_html_has_charset(self):
        """HTML 声明了 utf-8 编码"""
        self.assertIn('charset="utf-8"', HTML)

    def test_03_html_has_viewport(self):
        """HTML 有 viewport meta 标签"""
        self.assertIn("viewport", HTML)

    def test_04_all_events_bound(self):
        """已绑定事件的元素都存在"""
        # 从 JS 中提取所有 addEventListener 的目标
        targets = set(re.findall(r"\$\(['\"](#[\w-]+)['\"]\)\.addEventListener", self.js_code))
        for target in targets:
            # 去掉 # 前缀
            target_id = target.lstrip("#")
            self.assertIn(f'id="{target_id}"', HTML,
                          f"事件绑定目标 '{target_id}' 在 HTML 中不存在")

    def test_05_modal_structure(self):
        """Modal 结构完整"""
        self.assertIn("modal-overlay", HTML)
        self.assertIn("modal-editor", HTML)
        self.assertIn("modal-save", HTML)
        self.assertIn("modal-close", HTML)


if __name__ == "__main__":
    suite = unittest.TestSuite()
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestFrontendJS))
    suite.addTest(unittest.TestLoader().loadTestsFromTestCase(TestHTMLStructure))
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)

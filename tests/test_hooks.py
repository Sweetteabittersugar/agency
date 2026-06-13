"""Hooks 可执行性测试"""

import os

HOOKS_DIR = os.path.join(os.path.dirname(__file__), "..", "hooks")


def get_hook_files():
    """获取所有 hook 脚本"""
    if not os.path.isdir(HOOKS_DIR):
        return []
    return [f for f in os.listdir(HOOKS_DIR) if f.endswith(".sh")]


class TestHookScripts:
    """Hook 脚本基础检查"""

    def test_hooks_exist(self):
        hooks = get_hook_files()
        assert len(hooks) >= 4, f"期望至少 4 个 hook，实际 {len(hooks)}"

    REQUIRED_HOOKS = ["SessionStart.sh", "PostToolUse.sh", "PreCompact.sh", "Stop.sh"]

    def test_required_hooks_exist(self):
        for hook in self.REQUIRED_HOOKS:
            path = os.path.join(HOOKS_DIR, hook)
            assert os.path.isfile(path), f"缺少 hook: {hook}"

    def test_shebangs(self):
        """所有 hook 脚本必须以 #!/usr/bin/env bash 开头"""
        for hook_file in get_hook_files():
            path = os.path.join(HOOKS_DIR, hook_file)
            with open(path, "r", encoding="utf-8") as f:
                first_line = f.readline().strip()
            assert first_line == "#!/usr/bin/env bash", (
                f"{hook_file}: shebang 应为 '#!/usr/bin/env bash'，实际 '{first_line}'"
            )

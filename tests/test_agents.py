"""Agent 文件校验测试"""
import os
import pytest
import yaml

AGENTS_DIR = os.path.join(os.path.dirname(__file__), '..', 'agents')


def get_agent_files():
    """获取所有 agent 文件"""
    if not os.path.isdir(AGENTS_DIR):
        return []
    return [f for f in os.listdir(AGENTS_DIR) if f.endswith('.md')]


def parse_frontmatter(filepath):
    """解析 YAML frontmatter"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    if not content.startswith('---'):
        return None
    parts = content.split('---', 2)
    if len(parts) < 3:
        return None
    return yaml.safe_load(parts[1])


class TestAgentFrontmatter:
    """所有 agent 文件必须有合法的 YAML frontmatter"""

    REQUIRED_FIELDS = ['name', 'description', 'tools', 'model']
    VALID_MODELS = ['haiku', 'sonnet', 'opus']

    @pytest.mark.parametrize('agent_file', get_agent_files())
    def test_has_frontmatter(self, agent_file):
        filepath = os.path.join(AGENTS_DIR, agent_file)
        fm = parse_frontmatter(filepath)
        assert fm is not None, f"{agent_file}: 缺少 YAML frontmatter"

    @pytest.mark.parametrize('agent_file', get_agent_files())
    def test_required_fields(self, agent_file):
        filepath = os.path.join(AGENTS_DIR, agent_file)
        fm = parse_frontmatter(filepath)
        if fm is None:
            pytest.skip("无 frontmatter")
        for field in self.REQUIRED_FIELDS:
            assert field in fm, f"{agent_file}: 缺少必填字段 '{field}'"

    @pytest.mark.parametrize('agent_file', get_agent_files())
    def test_valid_model(self, agent_file):
        filepath = os.path.join(AGENTS_DIR, agent_file)
        fm = parse_frontmatter(filepath)
        if fm is None:
            pytest.skip("无 frontmatter")
        assert fm.get('model') in self.VALID_MODELS, \
            f"{agent_file}: model '{fm.get('model')}' 不在 {self.VALID_MODELS}"

    @pytest.mark.parametrize('agent_file', get_agent_files())
    def test_has_body(self, agent_file):
        filepath = os.path.join(AGENTS_DIR, agent_file)
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        parts = content.split('---', 2)
        assert len(parts) >= 3, f"{agent_file}: frontmatter 格式错误"
        body = parts[2].strip()
        assert len(body) > 50, f"{agent_file}: 正文过短 ({len(body)} 字符)"


class TestAgentCount:
    """Agent 数量检查"""

    def test_at_least_9_agents(self):
        files = get_agent_files()
        assert len(files) >= 9, f"期望至少 9 个 agent，实际 {len(files)}"

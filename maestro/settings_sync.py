"""隔离配置同步 — settings.json 合并 + agents/skills 复制到 .claude-isolated/"""
import json
import shutil
import logging
from pathlib import Path

log = logging.getLogger(__name__)


def sync_isolated_config(project_root: Path):
    """将全局 + 项目 settings 合并写入 .claude-isolated/，同步 agents 和 skills"""
    claude_dir = project_root / ".claude"
    claude_dir.mkdir(parents=True, exist_ok=True)
    isolated_path = project_root / ".claude-isolated"
    isolated_path.mkdir(parents=True, exist_ok=True)

    # 合并 settings.json
    merged = {}
    for src in [Path.home() / ".claude" / "settings.json", claude_dir / "settings.json"]:
        if src.exists():
            try:
                for k, v in json.loads(src.read_text(encoding="utf-8")).items():
                    if isinstance(v, dict) and k in merged:
                        merged[k].update(v)
                    else:
                        merged[k] = v
            except Exception:
                log.warning(f"Failed to merge settings from {src}")
    (isolated_path / "settings.json").write_text(
        json.dumps(merged, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    # 同步 agents
    dst_agents = isolated_path / "agents"
    dst_agents.mkdir(exist_ok=True)
    for src_dir in [project_root / "agents", claude_dir / "agents"]:
        if src_dir.exists():
            for f in src_dir.glob("*.md"):
                shutil.copy2(str(f), str(dst_agents / f.name))

    # 同步 skills
    for src_skills in [claude_dir / "skills", Path.home() / ".claude" / "skills"]:
        if src_skills.exists():
            dst_skills = isolated_path / "skills"
            dst_skills.mkdir(exist_ok=True)
            for sd in src_skills.iterdir():
                if sd.is_dir():
                    dest = dst_skills / sd.name
                    if not dest.exists():
                        shutil.copytree(str(sd), str(dest))

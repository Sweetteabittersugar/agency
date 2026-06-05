#!/usr/bin/env bash
# install.sh — agency-kit 安装脚本
# 将 agents/skills/commands/hooks/rules 链接到用户 Claude Code 配置目录

set -euo pipefail

# === 颜色 ===
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# === 路径解析 ===
SCRIPT_PATH="$0"
while [ -L "$SCRIPT_PATH" ]; do
    link_dir="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"
    SCRIPT_PATH="$(readlink "$SCRIPT_PATH")"
    [[ "$SCRIPT_PATH" != /* ]] && SCRIPT_PATH="$link_dir/$SCRIPT_PATH"
done
SCRIPT_DIR="$(cd "$(dirname "$SCRIPT_PATH")" && pwd)"

# === 目标目录 ===
# Claude Code 配置目录
CLAUDE_HOME="${CLAUDE_CONFIG_DIR:-$HOME/.claude}"
# 项目级别 → 当前工作目录的 .claude
PROJECT_CLAUDE="${CLAUDE_PROJECT_DIR:-$(pwd)}/.claude"

echo -e "${CYAN}╔══════════════════════════════════════╗${NC}"
echo -e "${CYAN}║   agency-kit 安装程序      ║${NC}"
echo -e "${CYAN}╚══════════════════════════════════════╝${NC}"
echo ""
echo -e "Agent 层 ${GREEN}不需要任何密钥${NC} — 装上就能用。"
echo -e "只有 Maestro 调度引擎需要 API key（可选）。"
echo ""

# === 选择安装目标 ===
echo "选择安装位置："
echo "  1) 全局 (~/.claude) — 所有项目生效"
echo "  2) 项目 (当前目录/.claude) — 仅当前项目"
echo "  3) 两者都装"
read -rp "请输入 (1/2/3，默认 2): " choice
choice="${choice:-2}"

install_to() {
    local target="$1"
    echo -e "${YELLOW}安装到: $target${NC}"

    # 创建目录
    mkdir -p "$target/agents" "$target/skills" "$target/commands" "$target/hooks" "$target/rules"

    # 复制 agents
    if [ -d "$SCRIPT_DIR/agents" ]; then
        cp -r "$SCRIPT_DIR/agents/"* "$target/agents/" 2>/dev/null || true
        echo -e "  ${GREEN}✓${NC} agents"
    fi

    # 复制 skills
    if [ -d "$SCRIPT_DIR/skills" ]; then
        cp -r "$SCRIPT_DIR/skills/"* "$target/skills/" 2>/dev/null || true
        echo -e "  ${GREEN}✓${NC} skills"
    fi

    # 复制 commands
    if [ -d "$SCRIPT_DIR/commands" ]; then
        cp -r "$SCRIPT_DIR/commands/"* "$target/commands/" 2>/dev/null || true
        echo -e "  ${GREEN}✓${NC} commands"
    fi

    # 复制 hooks
    if [ -d "$SCRIPT_DIR/hooks" ]; then
        cp -r "$SCRIPT_DIR/hooks/"* "$target/hooks/" 2>/dev/null || true
        echo -e "  ${GREEN}✓${NC} hooks"
    fi

    # 复制 rules
    if [ -d "$SCRIPT_DIR/rules" ]; then
        cp -r "$SCRIPT_DIR/rules/"* "$target/rules/" 2>/dev/null || true
        echo -e "  ${GREEN}✓${NC} rules"
    fi

    # 复制 maestro
    if [ -d "$SCRIPT_DIR/maestro" ]; then
        mkdir -p "$target/../maestro" 2>/dev/null || true
        cp -r "$SCRIPT_DIR/maestro/"* "$target/../maestro/" 2>/dev/null || true
        echo -e "  ${GREEN}✓${NC} maestro"
    fi
}

case "$choice" in
    1) install_to "$CLAUDE_HOME" ;;
    2) install_to "$PROJECT_CLAUDE" ;;
    3)
        install_to "$CLAUDE_HOME"
        echo ""
        install_to "$PROJECT_CLAUDE"
        ;;
    *)
        echo -e "${RED}无效选择，默认安装到项目${NC}"
        install_to "$PROJECT_CLAUDE"
        ;;
esac

echo ""
echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  安装完成！                          ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
echo ""
echo -e "${CYAN}📖 现在试试：${NC}"
echo ""
echo -e "  ${YELLOW}第 1 步${NC} — 在 Claude Code 中随便说句话"
echo -e "  ${YELLOW}第 2 步${NC} — 试试 @status 查看 agent 状态"
echo -e "  ${YELLOW}第 3 步${NC} — 试试 /design 进入设计模式"
echo ""
echo -e "${CYAN}📚 只装了 Agent，没装 Maestro？${NC}"
echo -e "  完全没问题。Agent 独立工作，Maestro 是给多 Agent 协作用的。"
echo -e "  大多数用户停在 Agent 层就够了。"
echo ""
echo -e "${CYAN}📖 想了解更多：${NC}"
echo -e "  cat GETTING-STARTED.md    # 5 分钟入门"
echo -e "  cat COMMANDS-QUICK-REF.md # 命令速查"
echo ""

# === Maestro 可选配置 ===
if [ -d "$SCRIPT_DIR/maestro" ]; then
    echo -e "${CYAN}⚡ 要启用 Maestro 调度引擎（可选）？${NC}"
    echo -e "  需要配置 DeepSeek API key。不用的话跳过，Agent 照样工作。"
    read -rp "  配置 Maestro？(y/N): " setup_maestro
    if [ "$setup_maestro" = "y" ] || [ "$setup_maestro" = "Y" ]; then
        if [ ! -f "$SCRIPT_DIR/.env" ]; then
            cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
            echo -e "  ${GREEN}✓${NC} 已创建 .env，请编辑填入你的 key："
            echo -e "  ${YELLOW}$SCRIPT_DIR/.env${NC}"
        fi
        echo ""
        echo -e "  需要填的 key："
        echo -e "    REASONIX_API_KEY=sk-xxxx    # DeepSeek API key"
        echo -e "  填好后运行：python maestro/dispatch.py --list"
    else
        echo -e "  跳过。以后想配：cp .env.example .env 然后编辑。"
    fi
fi

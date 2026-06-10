#!/usr/bin/env bash
# install.sh — Agency 一键安装脚本 (Linux/macOS)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

cat << 'EOF'

 ╔══════════════════════════════════════════════════╗
 ║       Agency — Claude Code Web 操作面板           ║
 ║       一键安装脚本 (Linux/macOS)                  ║
 ╚══════════════════════════════════════════════════╝

EOF

# ── 1. 检查 Python ──
echo "[1/5] 检查 Python..."
if ! command -v python3 &>/dev/null; then
    echo "  [错误] 未找到 Python3。请先安装 Python 3.10+"
    echo "  macOS: brew install python@3.11"
    echo "  Ubuntu: sudo apt install python3.11"
    exit 1
fi
PYVER=$(python3 --version 2>&1 | awk '{print $2}')
echo "  已安装 Python $PYVER"

# ── 2. 安装 Python 依赖 ──
echo ""
echo "[2/5] 安装 Python 依赖..."
pip3 install -e "$SCRIPT_DIR" --quiet 2>/dev/null || {
    echo "  [警告] pip install -e 失败，尝试普通安装..."
    pip3 install pyyaml requests --quiet
}
echo "  依赖安装完成"

# ── 3. 检查 Claude CLI ──
echo ""
echo "[3/5] 检查 Claude CLI..."
if command -v claude &>/dev/null; then
    echo "  Claude CLI 已就绪"
else
    echo "  [提示] 未找到 Claude CLI。Agent 调度功能将不可用。"
    echo "  安装: npm install -g @anthropic-ai/claude-code"
    echo "  没有 Claude API Key? 用 DeepSeek 也能跑 — 在设置页配置。"
fi

# ── 4. 首次配置 ──
echo ""
echo "[4/5] 首次配置..."
if [ ! -f "$SCRIPT_DIR/.env" ] && [ -f "$SCRIPT_DIR/.env.example" ]; then
    cp "$SCRIPT_DIR/.env.example" "$SCRIPT_DIR/.env"
    echo "  .env 已从模板创建"
fi
echo "  就绪！"

# ── 5. 创建桌面快捷方式 ──
echo ""
echo "[5/5] 创建桌面快捷方式..."
DESKTOP_DIR="${HOME}/Desktop"
if [ -d "$DESKTOP_DIR" ]; then
  cat > "$DESKTOP_DIR/Agency.desktop" << DESKTOPEOF
[Desktop Entry]
Name=Agency
Comment=Claude Code Web 操作面板
Exec=bash "$SCRIPT_DIR/start.sh"
Icon=applications-web
Terminal=false
Type=Application
Categories=Development;
DESKTOPEOF
  chmod +x "$DESKTOP_DIR/Agency.desktop"
  echo "  桌面快捷方式已创建: Agency"
else
  echo "  未找到桌面目录，跳过"
fi

# ── 完成 ──
cat << 'EOF'

 ╔══════════════════════════════════════════════════╗
 ║  安装完成！                                      ║
 ║                                                  ║
 ║  桌面已创建快捷方式，双击即可打开                 ║
 ║  或命令行: agency start                          ║
 ║                                                  ║
 ║  浏览器打开 http://localhost:8800                ║
 ║  无 API Key 也能浏览 Demo 界面                   ║
 ╚══════════════════════════════════════════════════╝

EOF

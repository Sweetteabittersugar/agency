#!/bin/bash
echo ""
echo "  ================================"
echo "  Agency Web UI"
echo "  ================================"
echo ""
echo "  Starting server at http://localhost:8800"
echo ""
# Open browser (macOS / Linux / WSL)
if command -v open &>/dev/null; then
    open http://localhost:8800
elif command -v xdg-open &>/dev/null; then
    xdg-open http://localhost:8800
elif command -v wslview &>/dev/null; then
    wslview http://localhost:8800
fi
python maestro/web.py

#!/bin/bash
# Station Calyx Launcher for Linux/macOS
# Make executable with: chmod +x calyx.sh

cd "$(dirname "$0")"

echo ""
echo "    ╭──────────────────────────────╮"
echo "    │    🌸 STATION CALYX 🌸       │"
echo "    │      AI-For-All Project      │"
echo "    ╰──────────────────────────────╯"
echo ""
echo "Starting Station Calyx Terminal UI..."
echo ""

python3 calyx.py "$@"

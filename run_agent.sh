#!/bin/bash
# Unified Agent Launcher
# Starts the always-connected AI agent

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

source "$SCRIPT_DIR/agent_env/bin/activate"

echo "🤖 Starting Unified Agent..."
python3 ev-ai-core/unified_agent.py "$@"

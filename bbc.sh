#!/bin/bash
# BBC Linux/macOS Launcher v8.3
# Usage: ./bbc.sh [command] [args]

set -e

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python 3 not found. Please install Python 3.8+"
    exit 1
fi

# BBC home directory (where bbc.py lives)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Verify BBC files exist
if [ ! -f "$SCRIPT_DIR/bbc.py" ]; then
    echo "[ERROR] BBC not found at $SCRIPT_DIR"
    exit 1
fi

# No arguments → default: start with current directory
if [ $# -eq 0 ]; then
    python3 "$SCRIPT_DIR/bbc.py" start "$(pwd)"
    exit $?
fi

# Commands that need current directory as default path
case "$1" in
    start|menu|analyze|audit|verify|purge)
        if [ $# -eq 1 ]; then
            python3 "$SCRIPT_DIR/bbc.py" "$1" "$(pwd)"
        else
            python3 "$SCRIPT_DIR/bbc.py" "$@"
        fi
        ;;
    stop|status|serve)
        python3 "$SCRIPT_DIR/bbc.py" "$@"
        ;;
    *)
        # Fallback: pass all arguments to run_bbc.py (bootstrap, inject, etc.)
        python3 "$SCRIPT_DIR/run_bbc.py" "$@"
        ;;
esac
exit $?

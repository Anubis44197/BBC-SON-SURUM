#!/bin/bash
# BBC v8.3 - One-Command Setup (Linux/Mac)
# Usage (recommended isolated mode):
#   1) Keep BBC in a central folder (outside projects)
#   2) cd your-project
#   3) bash /path/to/BBC/setup.sh [optional-project-path]
# Backward-compatible embedded usage also works.

echo ""
echo "============================================"
echo "  BBC v8.3 - One-Command Setup"
echo "============================================"
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 not found. Please install Python 3.10+ first."
    exit 1
fi

# Detect BBC home path
BBC_DIR="$(cd "$(dirname "$0")" && pwd)"

# Detect project path
if [ -n "$1" ]; then
    PROJECT_DIR="$(cd "$1" && pwd)"
else
    PROJECT_DIR="$(pwd)"
fi

# Backward compatibility: if setup is executed from BBC home itself, use parent as project
if [ "$PROJECT_DIR" = "$BBC_DIR" ]; then
    PROJECT_DIR="$(dirname "$BBC_DIR")"
fi

echo "[BBC] BBC directory:     $BBC_DIR"
echo "[BBC] Project directory:  $PROJECT_DIR"
echo ""

# Install dependencies
echo "[BBC] Step 1/2: Installing dependencies..."
python3 -m pip install -r "$BBC_DIR/requirements.txt" -q
if [ $? -ne 0 ]; then
    echo "[WARN] Some dependencies may have failed. Continuing..."
else
    echo "[BBC] Step 1/2: Dependencies installed."
fi

echo ""

# Run BBC start on the project
echo "[BBC] Step 2/2: Starting BBC on project..."
python3 "$BBC_DIR/bbc.py" start "$PROJECT_DIR"

echo ""
echo "[BBC] Setup complete."

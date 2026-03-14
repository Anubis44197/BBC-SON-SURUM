#!/bin/bash
# BBC v8.3 - One-Command Setup (Linux/Mac)
# Usage: Clone BBC into your project, then run this script
#   cd your-project
#   git clone https://github.com/Anubis44197/BBC.git
#   bash BBC/setup.sh

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

# Detect paths
BBC_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$BBC_DIR")"

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

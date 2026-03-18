#!/bin/bash
# BBC global uninstaller (clean model)
set -e

BBC_HOME="$(cd "$(dirname "$0")" && pwd)"
PROJECT_PATH="${1:-}"

echo "[BBC] Global uninstall starting"
echo "[BBC] BBC_HOME: $BBC_HOME"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERROR] python3 not found."
  exit 1
fi

if [ -n "$PROJECT_PATH" ]; then
  echo "[BBC] Cleaning project traces: $PROJECT_PATH"
  python3 "$BBC_HOME/bbc.py" uninstall "$PROJECT_PATH" --force || true
fi

python3 -m pip uninstall -y bbc-master bbc || true

for profile in "$HOME/.bashrc" "$HOME/.zshrc"; do
  if [ -f "$profile" ]; then
    if grep -q 'export BBC_HOME=' "$profile"; then
      tmp_file="${profile}.bbc.tmp"
      grep -v 'export BBC_HOME=' "$profile" > "$tmp_file" || true
      mv "$tmp_file" "$profile"
      echo "[BBC] Removed BBC_HOME export from $profile"
    fi
  fi
done

echo "[BBC] Global uninstall complete"

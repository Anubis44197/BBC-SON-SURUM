#!/bin/bash
# BBC global installer (clean model)
set -e

BBC_HOME="$(cd "$(dirname "$0")" && pwd)"

echo "[BBC] Global install starting"
echo "[BBC] BBC_HOME: $BBC_HOME"

if ! command -v python3 >/dev/null 2>&1; then
  echo "[ERROR] python3 not found. Install Python 3.8+ first."
  exit 1
fi

python3 -m pip install -r "$BBC_HOME/requirements.txt"
python3 -m pip install -e "$BBC_HOME"

# Persist BBC_HOME for future shells (best effort)
for profile in "$HOME/.bashrc" "$HOME/.zshrc"; do
  if [ -f "$profile" ]; then
    if ! grep -q 'export BBC_HOME=' "$profile"; then
      {
        echo ""
        echo "# BBC clean-model home"
        echo "export BBC_HOME=\"$BBC_HOME\""
      } >> "$profile"
      echo "[BBC] Added BBC_HOME to $profile"
    fi
  fi
done

if command -v bbc >/dev/null 2>&1; then
  echo "[BBC] CLI check passed: $(command -v bbc)"
  echo "[BBC] Try: bbc --help"
else
  echo "[WARN] 'bbc' command is not in PATH for this shell."
  echo "[WARN] Re-open terminal or use explicit command:"
  echo "      python3 \"$BBC_HOME/bbc.py\" --help"
fi

echo "[BBC] Global install complete"
echo "[BBC] Use on any project:"
echo "      cd <project> && bbc start ."

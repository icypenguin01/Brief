#!/usr/bin/env bash
set -euo pipefail

# ----------------------------
# Simple spinner for progress
# ----------------------------
spinner() {
  local pid=$!
  local delay=0.1
  local spinstr='|/-\'
  while ps -p $pid >/dev/null 2>&1; do
    local temp=${spinstr#?}
    printf " [%c]  " "$spinstr"
    spinstr=$temp${spinstr%"$temp"}
    sleep $delay
    printf "\b\b\b\b\b\b"
  done
  printf "    \b\b\b\b"
}

# ----------------------------------------
# Add auto-attach hook to ~/.bashrc
# ----------------------------------------
HOOK_LINE='[ -f ~/.brief/autoattach.sh ] && source ~/.brief/autoattach.sh'
PROFILE="${HOME}/.bashrc"

if ! grep -Fq "$HOOK_LINE" "$PROFILE"; then
  printf "\n# Brief auto-attach\n%s\n" "$HOOK_LINE" >> "$PROFILE"
  echo "[+] Added auto-attach hook to ${PROFILE}"
else
  echo "[*] Auto-attach hook already present in ${PROFILE}"
fi

# ----------------------------------------
# Install Python dependency (openai)
# ----------------------------------------
if command -v python3 >/dev/null 2>&1; then
  echo "[*] Upgrading pip (may take ~1 min)..."
  python3 -m pip install --upgrade pip >/dev/null 2>&1 &
  spinner

  echo "[*] Installing openai (may take ~1 min)..."
  python3 -m pip install openai >/dev/null 2>&1 &
  spinner

  echo "[+] Installed Python dependency: openai"
else
  echo "[!] python3 not found. Install Python 3 and run: python3 -m pip install openai"
fi

# ----------------------------------------
# Install brief binary
# ----------------------------------------
if [ -f "brief.py" ]; then
  sudo cp brief.py /usr/local/bin/brief
  sudo chmod +x /usr/local/bin/brief
  echo "[+] Installed brief to /usr/local/bin/brief"
else
  echo "[!] brief.py not found in current directory"
fi

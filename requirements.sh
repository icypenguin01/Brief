#!/usr/bin/env bash
set -euo pipefail

run_step() {
  local message="$1"
  shift
  echo "[*] ${message}..."
  "$@"
  echo "[+] ${message}"
}

# Add auto-attach hook to ~/.bashrc if not already present.
HOOK_LINE='[ -f ~/.brief/autoattach.sh ] && source ~/.brief/autoattach.sh'
PROFILE="${HOME}/.bashrc"
VENV_DIR="${HOME}/.brief/venv"

if ! grep -Fq "$HOOK_LINE" "$PROFILE"; then
  printf "\n# Brief auto-attach\n%s\n" "$HOOK_LINE" >> "$PROFILE"
  echo "[+] Added auto-attach hook to ${PROFILE}"
else
  echo "[*] Auto-attach hook already present in ${PROFILE}"
fi

if command -v python3 >/dev/null 2>&1; then
  mkdir -p "${HOME}/.brief"
  if [ ! -d "${VENV_DIR}" ]; then
    run_step "Creating Python virtual environment at ${VENV_DIR}" python3 -m venv "${VENV_DIR}"
  else
    echo "[*] Using existing Python virtual environment at ${VENV_DIR}"
  fi

  run_step "Upgrading pip in virtual environment" "${VENV_DIR}/bin/python" -m pip install --upgrade pip
  run_step "Installing openai in virtual environment" "${VENV_DIR}/bin/python" -m pip install openai
  echo "[+] Installed Python dependency: openai (venv)"
else
  echo "[!] python3 not found. Install Python 3 and run this script again."
fi

if [ -f "brief.py" ]; then
  if [ -x "${VENV_DIR}/bin/python" ]; then
    TMP_BRIEF="$(mktemp)"
    {
      printf "#!%s\n" "${VENV_DIR}/bin/python"
      awk 'NR == 1 && /^#!/ { next } { print }' brief.py
    } > "${TMP_BRIEF}"
    run_step "Installing brief to /usr/local/bin/brief (mode 0755)" sudo install -m 0755 "${TMP_BRIEF}" /usr/local/bin/brief
    rm -f "${TMP_BRIEF}"
    echo "[+] Installed brief to /usr/local/bin/brief (uses venv Python)"
  else
    run_step "Installing brief to /usr/local/bin/brief (mode 0755)" sudo install -m 0755 brief.py /usr/local/bin/brief
    echo "[+] Installed brief to /usr/local/bin/brief"
  fi
else
  echo "[!] brief.py not found in current directory"
fi

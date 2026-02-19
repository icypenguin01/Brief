#!/usr/bin/env bash
set -euo pipefail

run_step() {
  local message="$1"
  shift
  echo "[*] ${message}..."
  "$@"
  echo "[+] ${message}"
}

target_user() {
  if [ -n "${SUDO_USER:-}" ] && [ "${SUDO_USER}" != "root" ]; then
    printf "%s" "${SUDO_USER}"
  else
    id -un
  fi
}

target_home() {
  local user="$1"
  if command -v getent >/dev/null 2>&1; then
    getent passwd "${user}" | cut -d: -f6
  else
    eval "printf '%s' \"~${user}\""
  fi
}

run_as_target() {
  local user="$1"
  shift
  if [ "$(id -un)" = "${user}" ]; then
    "$@"
  else
    sudo -H -u "${user}" "$@"
  fi
}

install_brief_binary() {
  local source_py="$1"
  local lib_dir="$2"
  local bin_path="$3"

  sudo install -d -m 0755 "${lib_dir}"
  sudo install -m 0755 "${source_py}" "${lib_dir}/brief.py"

  local tmp
  tmp="$(mktemp)"
  cat > "${tmp}" <<'EOF'
#!/usr/bin/env bash
set -euo pipefail

resolve_home() {
  if [ -n "${SUDO_USER:-}" ] && [ "${SUDO_USER}" != "root" ] && command -v getent >/dev/null 2>&1; then
    local sudo_home
    sudo_home="$(getent passwd "${SUDO_USER}" | cut -d: -f6)"
    if [ -n "${sudo_home}" ]; then
      printf "%s" "${sudo_home}"
      return
    fi
  fi
  printf "%s" "${HOME}"
}

TARGET_HOME="$(resolve_home)"
VENV_PY="${TARGET_HOME}/.brief/venv/bin/python"
BRIEF_SCRIPT="/usr/local/lib/brief/brief.py"

if [ ! -x "${VENV_PY}" ]; then
  echo "[-] brief runtime not found: ${VENV_PY}" >&2
  echo "[!] Run ./requirements.sh for this user first." >&2
  exit 2
fi

exec "${VENV_PY}" "${BRIEF_SCRIPT}" "$@"
EOF
  sudo install -m 0755 "${tmp}" "${bin_path}"
  rm -f "${tmp}"
}

install_brief_wrapper() {
  local user="$1"
  local home="$2"
  local bashrc="${home}/.bashrc"
  local begin="# >>> brief command wrapper >>>"
  local end="# <<< brief command wrapper <<<"

  run_as_target "${user}" bash -lc "touch '${bashrc}'"
  run_as_target "${user}" bash -lc "tmp=\$(mktemp); \
    awk -v b='${begin}' -v e='${end}' 'BEGIN{skip=0} \$0==b{skip=1;next} \$0==e{skip=0;next} !skip{print}' '${bashrc}' > \"\$tmp\"; \
    printf '%s\n' \
      '${begin}' \
      'brief() {' \
      '  command /usr/local/bin/brief \"\$@\"' \
      '  local rc=\$?' \
      '  if [ -f \"\$HOME/.brief/.brief_shell_rc\" ]; then' \
      '    source \"\$HOME/.brief/.brief_shell_rc\" > /dev/null 2>&1 || true' \
      '  fi' \
      '  # Hide background job notifications like \"[1] 81070\".' \
      '  set +m > /dev/null 2>&1 || true' \
      '  return \$rc' \
      '}' \
      '${end}' >> \"\$tmp\"; \
    mv \"\$tmp\" '${bashrc}'"
}

ensure_cmd() {
  local cmd="$1"
  local pkg="$2"
  if command -v "${cmd}" >/dev/null 2>&1; then
    echo "[*] ${cmd} already installed"
  else
    run_step "Installing ${pkg}" sudo apt-get install -y "${pkg}"
  fi
}

if ! command -v apt-get >/dev/null 2>&1; then
  echo "[-] This script currently supports Debian/Ubuntu (apt-get) only."
  echo "[!] Install these manually on your distro:"
  echo "    bash util-linux python3 python3-venv python3-pip"
  exit 2
fi

run_step "Updating apt cache" sudo apt-get update

ensure_cmd bash bash
ensure_cmd flock util-linux
ensure_cmd python3 python3
ensure_cmd pip3 python3-pip

# python3 -m venv can be missing even if python3 exists.
run_step "Installing python3-venv" sudo apt-get install -y python3-venv

TARGET_USER="$(target_user)"
TARGET_HOME="$(target_home "${TARGET_USER}")"
if [ -z "${TARGET_HOME}" ]; then
  echo "[-] Could not resolve home directory for user: ${TARGET_USER}"
  exit 2
fi
BRIEF_HOME="${TARGET_HOME}/.brief"
VENV_DIR="${BRIEF_HOME}/venv"
SESS_DIR="${BRIEF_HOME}/sessions"
OUT_DIR="${BRIEF_HOME}/outputs"
TMP_DIR="${BRIEF_HOME}/tmp"
CURRENT_FILE="${BRIEF_HOME}/.current_session"
META_FILE="${BRIEF_HOME}/.current_session_meta.json"
BRIEF_BIN="/usr/local/bin/brief"
BRIEF_LIB_DIR="/usr/local/lib/brief"

run_step "Creating ${BRIEF_HOME} for ${TARGET_USER}" sudo mkdir -p "${BRIEF_HOME}"
run_step "Creating brief folders" sudo mkdir -p "${SESS_DIR}" "${OUT_DIR}" "${TMP_DIR}"
run_step "Setting ownership on ${BRIEF_HOME}" sudo chown -R "${TARGET_USER}:${TARGET_USER}" "${BRIEF_HOME}"

if [ ! -f "${CURRENT_FILE}" ]; then
  run_step "Initializing recording state file" run_as_target "${TARGET_USER}" bash -lc "printf '/dev/null\n' > '${CURRENT_FILE}'"
fi
if [ ! -f "${META_FILE}" ]; then
  run_step "Initializing metadata file" run_as_target "${TARGET_USER}" bash -lc "printf '{}\n' > '${META_FILE}'"
fi
run_step "Fixing ownership for state/metadata files" sudo chown "${TARGET_USER}:${TARGET_USER}" "${CURRENT_FILE}" "${META_FILE}"

if [ ! -d "${VENV_DIR}" ]; then
  run_step "Creating virtual environment at ${VENV_DIR}" run_as_target "${TARGET_USER}" python3 -m venv "${VENV_DIR}"
else
  echo "[*] Using existing virtual environment at ${VENV_DIR}"
fi

run_step "Upgrading pip in virtual environment" run_as_target "${TARGET_USER}" "${VENV_DIR}/bin/python" -m pip install --upgrade pip
run_step "Installing Python dependency: openai" run_as_target "${TARGET_USER}" "${VENV_DIR}/bin/python" -m pip install openai

if [ -f "brief.py" ]; then
  run_step "Installing brief runtime in ${BRIEF_LIB_DIR}" install_brief_binary "brief.py" "${BRIEF_LIB_DIR}" "${BRIEF_BIN}"
  run_step "Ensuring brief launcher is executable" sudo chmod 0755 "${BRIEF_BIN}"
  run_step "Installing brief wrapper in ${TARGET_HOME}/.bashrc" install_brief_wrapper "${TARGET_USER}" "${TARGET_HOME}"
else
  echo "[!] brief.py not found in current directory; skipped brief install"
fi

run_step "Smoke test brief under ${TARGET_USER}" run_as_target "${TARGET_USER}" env HOME="${TARGET_HOME}" bash -lc "'${BRIEF_BIN}' --list > /dev/null 2>&1"

echo
echo "[+] Requirements installed."
echo "[*] Optional: export HF_TOKEN=hf_xxxxxxxxxxxxxxxxx"
echo "[*] Installed binary: ${BRIEF_BIN}"
echo "[*] User home used for data: ${TARGET_HOME}"
echo "[+] start using Brief using brief --start."
echo "[+] Have any query do 'brief --help'"

if [ "$(id -un)" = "${TARGET_USER}" ] && [ -t 0 ] && [ -t 1 ]; then
  echo "[*] Brief installed. Auto-reloading shell in 2 seconds..."
  sleep 2
  exec bash -i
fi

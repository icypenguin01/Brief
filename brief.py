#!/usr/bin/env python3

import os
import argparse
import time
import threading
import textwrap
import shutil
import re
from pathlib import Path
from datetime import datetime, timezone
import sys
import json
import platform

# =========================
# VERSION
# =========================

VERSION = "1.0.0"

# =========================
# CONFIG
# =========================

def _brief_home_dir() -> Path:
    """
    When `brief` is run under sudo, we still want to read/write sessions under the invoking user's HOME,
    not `/root`.
    """
    if platform.system().lower() == "windows":
        return Path.home()

    def _home_from_user(user: str) -> Path | None:
        if not user:
            return None
        try:
            import pwd  # type: ignore

            return Path(pwd.getpwnam(user).pw_dir)
        except Exception:
            return None

    def _home_from_uid(uid: int) -> Path | None:
        try:
            import pwd  # type: ignore

            return Path(pwd.getpwuid(uid).pw_dir)
        except Exception:
            return None

    def _fallback_non_root_home() -> Path | None:
        for key in ("LOGNAME", "USER", "USERNAME"):
            user = os.environ.get(key, "").strip()
            if user and user != "root":
                home = _home_from_user(user)
                if home:
                    return home
        try:
            st = os.stat(os.getcwd())
            if st.st_uid != 0:
                home = _home_from_uid(st.st_uid)
                if home:
                    return home
        except Exception:
            pass
        return None

    sudo_user = os.environ.get("SUDO_USER", "").strip()
    if sudo_user and sudo_user != "root":
        home = _home_from_user(sudo_user)
        if home:
            return home
    sudo_uid = os.environ.get("SUDO_UID", "").strip()
    if sudo_uid.isdigit():
        home = _home_from_uid(int(sudo_uid))
        if home:
            return home
    # Prefer real user id home over env to avoid wrong inherited HOME (e.g., /root).
    home = _home_from_uid(os.getuid())
    if home:
        return home
    # Then try effective user.
    home = _home_from_uid(os.geteuid())
    if home:
        return home
    home_env = os.environ.get("HOME", "").strip()
    if home_env and home_env != "/root":
        return Path(home_env)
    home = Path.home()
    if str(home) == "/root":
        fallback = _fallback_non_root_home()
        if fallback:
            return fallback
    return home

HOME_DIR = _brief_home_dir()
# Hard guard: if process is not root, never use /root as storage home.
_geteuid = getattr(os, "geteuid", lambda: 0)
if str(HOME_DIR) == "/root" and _geteuid() != 0:
    HOME_DIR = Path.home()
BASE_DIR = HOME_DIR / ".brief"
SESS_DIR = BASE_DIR / "sessions"
OUT_DIR = BASE_DIR / "outputs"
TMP_DIR = BASE_DIR / "tmp"
CURRENT_SESSION_FILE = BASE_DIR / ".current_session"
CURRENT_SESSION_META_FILE = BASE_DIR / ".current_session_meta.json"
SHELL_RCFILE = BASE_DIR / ".brief_shell_rc"
BASHRC_FILE = HOME_DIR / ".bashrc"
DEVNULL_ROUTE = "/dev/null"
HOOK_BEGIN = "# >>> brief shell hook >>>"
HOOK_END = "# <<< brief shell hook <<<"

HF_BASE_URL = "https://router.huggingface.co/v1"
MODEL = "openai/gpt-oss-120b:novita"

# =========================
# PROMPT
# =========================

PROMPT_TEMPLATE = (
    "i just sloved vunrable box or machine. This is my command history. "
    "roast my history like a strict but helpful mentor. point out every mistake, "
    "explain why it was wrong, what i misunderstood, and what bad habit it shows. "
    "show the correct methodology, better command choices, and improved workflow. "
    "go step by step, go deep, and explain the thinking process so i can learn and "
    "not repeat the same mistakes.\n\n"
    "{{SESSION}}\n"
)

# =========================
# HTML TEMPLATE
# =========================

HTML_TEMPLATE = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>CTF Brief Report</title>
    <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        html, body {
            width: 100%;
            height: 100%;
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
            line-height: 1.6;
            color: #5a6b63;
            background: #f8f9f7;
        }
        
        .page-wrapper {
            min-height: 100vh;
            padding: 0;
            margin: 0;
            display: flex;
            align-items: stretch;
            justify-content: center;
        }
        
        .report-container {
            width: 100%;
            background: #fafbf9;
            box-shadow: none;
            border-radius: 0;
            overflow: auto;
            display: flex;
            flex-direction: column;
        }
        
        .report-header {
            background: linear-gradient(135deg, #1a1a1a 0%, #2d2d2d 100%);
            color: #ffffff;
            padding: 120px 60px;
            text-align: left;
            flex-shrink: 0;
            border-bottom: 4px solid #9ba899;
        }
        
        .report-header h1 {
            font-size: 4.2em;
            margin-bottom: 25px;
            font-weight: 800;
            letter-spacing: -1px;
            line-height: 1.1;
            color: #ffffff;
        }
        
        .report-header p {
            font-size: 1.4em;
            opacity: 1;
            font-weight: 400;
            letter-spacing: 0.5px;
            color: #ffffff;
        }
        
        .report-content {
            padding: 60px 80px;
            flex: 1;
        }
        
        .intro-section {
            margin-bottom: 40px;
            padding: 20px;
            background: #f0f2f0;
            border-left: 4px solid #9ba899;
            border-radius: 4px;
        }
        
        .intro-section p {
            margin-bottom: 10px;
            color: #555;
        }
        
        .intro-section strong {
            color: #333;
        }
        
        /* Section styling */
        .report-section {
            margin-bottom: 50px;
        }
        
        .section-header {
            display: flex;
            align-items: center;
            margin-bottom: 25px;
            padding-bottom: 15px;
            border-bottom: 2px solid #d4d8d2;
        }
        
        .section-number {
            display: flex;
            align-items: center;
            justify-content: center;
            width: 35px;
            height: 35px;
            background: #9ba899;
            color: #fafbf9;
            border-radius: 50%;
            font-weight: bold;
            margin-right: 15px;
            flex-shrink: 0;
        }
        
        .section-title {
            font-size: 1.8em;
            color: #333;
            font-weight: 600;
        }
        
        /* Heading styles */
        h1 {
            font-size: 2.2em;
            color: #333;
            margin-bottom: 20px;
            margin-top: 30px;
        }
        
        h1:first-child {
            margin-top: 0;
        }
        
        h2 {
            font-size: 1.6em;
            color: #682f21;
            margin-bottom: 15px;
            margin-top: 25px;
        }
        
        h3 {
            font-size: 1.2em;
            color: #3e0707;
            margin-bottom: 12px;
            margin-top: 20px;
        }
        
        /* Paragraph and text */
        p {
            margin-bottom: 15px;
            text-align: justify;
            line-height: 1.8;
            color: #555;
        }
        
        /* Lists */
        ul, ol {
            margin-left: 30px;
            margin-bottom: 15px;
        }
        
        li {
            margin-bottom: 10px;
            line-height: 1.8;
            color: #555;
        }
        
        /* Code styling */
        code {
            background: #f5f5f5;
            padding: 3px 8px;
            border-radius: 3px;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
            color: #d63384;
        }
        
        pre {
            background: #2d2d2d;
            color: #f8f8f2;
            padding: 20px;
            border-radius: 6px;
            overflow-x: auto;
            margin-bottom: 20px;
            line-height: 1.5;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }
        
        pre code {
            background: none;
            padding: 0;
            color: inherit;
        }
        
        /* Blockquote */
        blockquote {
            border-left: 4px solid #9ba899;
            padding: 15px 20px;
            margin: 20px 0;
            background: #f0f2f0;
            border-radius: 4px;
            color: #5a6b63;
            font-style: italic;
        }
        
        /* Table styling */
        table {
            width: 100%;
            border-collapse: collapse;
            margin: 25px 0;
            box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
            border-radius: 6px;
            overflow: hidden;
        }
        
        thead {
            background: #9ba899;
            color: #fafbf9;
        }
        
        th {
            padding: 16px;
            text-align: left;
            font-weight: 600;
            font-size: 0.95em;
        }
        
        td {
            padding: 14px 16px;
            border-bottom: 1px solid #e0e0e0;
            color: #555;
        }
        
        tbody tr:hover {
            background: #f0f2f0;
        }
        
        tbody tr:last-child td {
            border-bottom: none;
        }
        
        /* Emphasis styles */
        strong {
            color: #000;
            font-weight: 600;
        }
        
        em {
            color: #7a8c79;
        }
        
        /* Links */
        a {
            color: #7a8c79;
            text-decoration: none;
            border-bottom: 1px solid #7a8c79;
            transition: all 0.3s ease;
        }
        
        a:hover {
            color: #9ba899;
            border-bottom-color: #9ba899;
        }
        
        /* Horizontal rule */
        hr {
            border: none;
            height: 2px;
            background: linear-gradient(90deg, transparent, #9ba899, transparent);
            margin: 40px 0;
        }
        
        /* Print styles */
        @media print {
            body {
                background: white;
            }
            
            .page-wrapper {
                padding: 0;
            }
            
            .report-container {
                box-shadow: none;
                max-width: 100%;
            }
            
            .report-header {
                page-break-after: avoid;
            }
        }
        
        /* Responsive */
        @media (max-width: 768px) {
            .report-header {
                padding: 40px 30px;
            }
            
            .report-header h1 {
                font-size: 1.8em;
            }
            
            .report-content {
                padding: 30px;
            }
            
            table {
                font-size: 0.9em;
            }
            
            th, td {
                padding: 10px 12px;
            }
        }
    </style>
</head>
<body>
    <div class="page-wrapper">
        <div class="report-container">
            <div class="report-header">
                <h1>After-Action Report By Brief (AARB)</h1>
                <p>Below is a step-by-step review of your CTF command history, highlighting methodological mistakes, incorrect assumptions, and inefficient habits.<br>Each section explains why the approach was ineffective, what assumptions led to it, and presents a correct, repeatable workflow for future engagements.</p>
            </div>
            
            <div class="report-content" id="content">
                <p>Loading report...</p>
            </div>
        </div>
    </div>
    
    <script id="markdown-data" type="application/json">
{{MARKDOWN_JSON}}
    </script>
    
    <script>
        // Get markdown content from script tag
        document.addEventListener('DOMContentLoaded', function() {
            const contentDiv = document.getElementById('content');
            const scriptTag = document.getElementById('markdown-data');
            
            if (scriptTag && scriptTag.textContent) {
                try {
                    const markdownContent = JSON.parse(scriptTag.textContent);
                    contentDiv.innerHTML = marked.parse(markdownContent);
                } catch (e) {
                    contentDiv.innerHTML = '<p style="color: red;">Error loading markdown: ' + e.message + '</p>';
                    console.error(e);
                }
            } else {
                contentDiv.innerHTML = '<p style="color: red;">No markdown content found</p>';
            }
        });
    </script>
</body>
</html>
'''

# =========================
# UTILS
# =========================

BOX_INNER_WIDTH = 62
HELP_BOX_WIDTH = 78

def ensure_dirs():
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    SESS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    TMP_DIR.mkdir(parents=True, exist_ok=True)

def _is_linux():
    return platform.system().lower() == "linux"

def _require_recording_tools():
    if not shutil.which("bash"):
        print("[-] bash not found")
        print("[!] Install: sudo apt-get install -y bash")
        sys.exit(2)
    # util-linux provides `flock`, which we use for safe concurrent appends.
    if not shutil.which("flock"):
        print("[-] flock not found")
        print("[!] Install: sudo apt-get install -y util-linux")
        sys.exit(2)

def _write_shell_rcfile():
    """
    Global bash hook sourced from ~/.bashrc.
    It logs interactive commands and routes output to:
      - /dev/null by default
      - the active session file after `brief --start`/`brief --use`
    """
    ensure_dirs()
    rc = r"""# brief global shell hook

__brief_base="${HOME}/.brief"
__brief_current="${__brief_base}/.current_session"
__brief_lock="${__brief_base}/.lock"
__brief_default="/dev/null"

__brief_ts() { date -u '+%Y-%m-%dT%H:%M:%SZ'; }

__brief_should_log() {
  [ -z "${PS1:-}" ] && return 1
  return 0
}

# Avoid job-control notifications like "[1] 81070" from helper processes.
set +m >/dev/null 2>&1 || true

_brief_complete() {
  local cur prev opts
  COMPREPLY=()
  cur="${COMP_WORDS[COMP_CWORD]}"
  prev=""
  if [ "${COMP_CWORD}" -gt 0 ]; then
    prev="${COMP_WORDS[COMP_CWORD-1]}"
  fi

  opts="--version --start --use --list --reports --tail --ingest --latest --stop --active -v -s -u -l -r -t -i -la -as -st -h --help"

  case "${prev}" in
    --use|-u|--ingest|-i)
      COMPREPLY=( $(compgen -f -- "${cur}") )
      return 0
      ;;
    --active|-as)
      COMPREPLY=( $(compgen -W "session" -- "${cur}") )
      return 0
      ;;
  esac

  COMPREPLY=( $(compgen -W "${opts}" -- "${cur}") )
  return 0
}

complete -o default -F _brief_complete brief 2>/dev/null || true

__brief_route() {
  local log_file
  log_file="$(cat "${__brief_current}" 2>/dev/null | tr -d '\r\n')"
  [ -n "${log_file}" ] || log_file="${__brief_default}"
  printf '%s' "${log_file}"
}

__brief_skip_cmd() {
  local cmd="$1"

  # Do not log brief control commands.
  case "${cmd}" in
    brief\ --start*|brief\ --stop*|brief\ --active*|brief\ -i\ *|brief\ --ingest\ *|brief\ --use\ *|brief\ -u\ * )
      return 0
      ;;
    /usr/local/bin/brief\ --start*|/usr/local/bin/brief\ --stop*|/usr/local/bin/brief\ --active*|/usr/local/bin/brief\ -i\ *|/usr/local/bin/brief\ --ingest\ *|/usr/local/bin/brief\ --use\ *|/usr/local/bin/brief\ -u\ * )
      return 0
      ;;
    sudo\ brief\ --start*|sudo\ brief\ --stop*|sudo\ brief\ --active*|sudo\ brief\ -i\ *|sudo\ brief\ --ingest\ *|sudo\ brief\ --use\ *|sudo\ brief\ -u\ * )
      return 0
      ;;
    sudo\ ./autorun.sh*|./autorun.sh*|sudo\ /home/*/autorun.sh*|/home/*/autorun.sh* )
      return 0
      ;;
  esac

  # Basic secret/token filters (best-effort).
  case "${cmd}" in
    *"HF_TOKEN="*|*"OPENAI_API_KEY="*|*"API_KEY="*|*"password"*|*"passphrase"*|*"otp"*|*"2fa"* )
      return 0
      ;;
  esac
  return 1
}

__brief_append() {
  local source="$1"
  local rc="$2"
  local cwd="$3"
  local cmd="$4"
  local log_file

  [ -n "${cmd}" ] || return 0
  log_file="$(__brief_route)"
  [ -n "${log_file}" ] || log_file="${__brief_default}"

  mkdir -p "${__brief_base}/sessions" "${__brief_base}/outputs" "${__brief_base}/tmp" 2>/dev/null
  {
    flock -w 1 9 || true
    printf '%s\t%s\t%s\t[%s]\t%s\n' "$(__brief_ts)" "${rc}" "${cwd}" "${source}" "${cmd}" >> "${log_file}" 2>&1
  } 9>"${__brief_lock}"
}

__brief_build_cmdline() {
  local base="$1"
  shift
  local out="${base}"
  local arg
  for arg in "$@"; do
    out="${out} ${arg}"
  done
  printf '%s' "${out}"
}

__brief_clean_line() {
  local line="$1"
  line="${line%$'\r'}"
  # Strip common ANSI escape sequences and NUL bytes.
  line="$(printf '%s' "${line}" | sed -E 's/\x1B\[[0-9;?]*[[:alpha:]]//g')"
  line="$(printf '%s' "${line}" | sed -E "s/\x1B\][^\a]*\a//g")"
  line="$(printf '%s' "${line}" | tr -d '\000')"
  printf '%s' "${line}"
}

__brief_parse_remote_output_stream() {
  local origin_pwd="$1"
  local source_label="$2"
  local count_file="$3"
  local line clean cmd prompt entry last_entry pending_prompt

  pending_prompt=""
  while IFS= read -r line; do
    clean="$(__brief_clean_line "${line}")"
    clean="$(printf '%s' "${clean}" | sed -E 's/[[:space:]]+$//')"
    [ -n "${clean}" ] || continue

    case "${clean}" in
      Script\ started\ on*|Script\ done\ on* )
        continue
        ;;
      Listening\ on*|Connection\ received\ on* )
        continue
        ;;
      bash:\ cannot\ set\ terminal\ process\ group*|bash:\ no\ job\ control\ in\ this\ shell* )
        continue
        ;;
    esac

    cmd=""
    prompt=""
    entry=""

    # Inline prompt + command (portable extraction; avoids BASH_REMATCH dependency).
    prompt="$(printf '%s' "${clean}" | sed -nE 's/^([^[:space:]]+@[^:]+:.*[$#])[[:space:]]*.+$/\1/p')"
    cmd="$(printf '%s' "${clean}" | sed -nE 's/^[^[:space:]]+@[^:]+:.*[$#][[:space:]]*(.+)$/\1/p')"
    if [ -n "${prompt}" ] && [ -n "${cmd}" ]; then
      pending_prompt=""
    else
      prompt="$(printf '%s' "${clean}" | sed -nE 's/^([^[:space:]]+@[^:]+:.*[$#])[[:space:]]*$/\1/p')"
      if [ -n "${prompt}" ]; then
        pending_prompt="${prompt}"
        continue
      elif [ -n "${pending_prompt:-}" ]; then
        prompt="${pending_prompt}"
        cmd="${clean}"
        pending_prompt=""
      fi
    fi

    [ -n "${cmd}" ] || continue
    cmd="$(printf '%s' "${cmd}" | sed -E 's/^[;[:space:]]+//; s/[[:space:]]+$//')"
    [ -n "${cmd}" ] || continue
    __brief_skip_cmd "${cmd}" && continue

    entry="${prompt} ${cmd}"
    entry="$(printf '%s' "${entry}" | sed -E 's/[[:space:]]+$//')"
    if [ "${entry}" = "${last_entry:-}" ]; then
      continue
    fi
    last_entry="${entry}"

    __brief_append "${source_label}" 0 "${origin_pwd}" "${entry}"
    if [ -n "${count_file}" ]; then
      printf '1\n' >> "${count_file}"
    fi
  done
}

__brief_parse_remote_output_commands() {
  local source_file="$1"
  local origin_pwd="$2"
  local source_label="$3"
  local count_file output_count

  [ -f "${source_file}" ] || { printf '0'; return 0; }
  count_file="$(mktemp "${__brief_base}/tmp/remote.parse.XXXXXX")" || { printf '0'; return 0; }
  __brief_parse_remote_output_stream "${origin_pwd}" "${source_label}" "${count_file}" < <(tr '\r' '\n' < "${source_file}")
  output_count="$(wc -l < "${count_file}" 2>/dev/null | tr -d '[:space:]')"
  rm -f "${count_file}" >/dev/null 2>&1 || true
  [ -n "${output_count}" ] || output_count=0
  printf '%s' "${output_count}"
}

__brief_capture_remote_input_commands() {
  local input_log="$1"
  local origin_pwd="$2"
  local source_label="$3"
  local cmd last_cmd count

  [ -f "${input_log}" ] || return 0
  count=0

  while IFS= read -r cmd; do
    cmd="$(printf '%s' "${cmd}" | tr -d '\000')"
    cmd="$(printf '%s' "${cmd}" | sed -E 's/\x1B\[[0-9;?]*[[:alpha:]]//g')"
    cmd="$(printf '%s' "${cmd}" | sed -E 's/[\x01-\x08\x0B\x0C\x0E-\x1F\x7F]//g')"
    cmd="$(printf '%s' "${cmd}" | sed -E 's/^[[:space:]]+//; s/[[:space:]]+$//')"
    [ -n "${cmd}" ] || continue

    case "${cmd}" in
      *"[2004h"*|*"[2004l"* )
        continue
        ;;
      Script\ started\ on*|Script\ done\ on* )
        continue
        ;;
      Listening\ on*|Connection\ received\ on* )
        continue
        ;;
      bash:\ cannot\ set\ terminal\ process\ group*|bash:\ no\ job\ control\ in\ this\ shell* )
        continue
        ;;
    esac

    __brief_skip_cmd "${cmd}" && continue
    if [ "${cmd}" = "${last_cmd:-}" ]; then
      continue
    fi
    last_cmd="${cmd}"
    __brief_append "${source_label}" 0 "${origin_pwd}" "${cmd}"
    count=$((count + 1))
  done < <(tr '\r' '\n' < "${input_log}")
  printf '%s' "${count}"
}

__brief_log_last() {
  local rc=$?
  __brief_should_log || return 0

  local h num cmd

  # Ensure history captures everything (avoid HISTCONTROL dropping duplicates).
  if [ -n "${ZSH_VERSION:-}" ]; then
    setopt APPEND_HISTORY >/dev/null 2>&1 || true
    h="$(fc -ln -1 2>/dev/null)" || return 0
    cmd="$(printf '%s' "${h}" | tail -n 1)" || return 0
    [ -n "${cmd}" ] || return 0
    cmd="$(printf '%s' "${cmd}" | sed -E 's/^[[:space:]]+//')"
    num="${cmd}"
  else
    export HISTCONTROL=
    shopt -s histappend >/dev/null 2>&1 || true
    h="$(history 1 2>/dev/null)" || return 0
    num="$(printf '%s' "${h}" | sed -E 's/^ *([0-9]+).*/\1/')" || return 0
    cmd="$(printf '%s' "${h}" | sed -E 's/^ *[0-9]+ *//')" || return 0
    [ -n "${cmd}" ] || return 0
    cmd="$(printf '%s' "${cmd}" | sed -E 's/^[[:space:]]+//')"
  fi

  # Deduplicate: PROMPT_COMMAND can run multiple times.
  if [ "${__BRIEF_LAST_HISTNUM:-}" = "${num}" ]; then
    return 0
  fi
  __BRIEF_LAST_HISTNUM="${num}"

  if [ "${__BRIEF_SKIP_NEXT_REMOTE_HIST:-0}" = "1" ]; then
    case "${cmd}" in
      nc|nc\ *|ncat|ncat\ *|netcat|netcat\ *|ssh|ssh\ *|telnet|telnet\ *|socat|socat\ *|rlwrap|rlwrap\ *|ftp|ftp\ *|sftp|sftp\ *|rlogin|rlogin\ *|rsh|rsh\ * )
        __BRIEF_SKIP_NEXT_REMOTE_HIST=0
        return 0
        ;;
      * )
        __BRIEF_SKIP_NEXT_REMOTE_HIST=0
        ;;
    esac
  fi

  __brief_skip_cmd "${cmd}" && return 0
  __brief_append "from shell" "${rc}" "${PWD}" "${cmd}"
}

__brief_remote_wrapper() {
  local bin_name="$1"
  local source_label="$2"
  shift 2

  if ! __brief_should_log; then
    command "${bin_name}" "$@"
    return $?
  fi

  local log_file transcript stdin_log nc_rc start_pwd used_script run_cmd output_count allow_input_fallback
  local launch_cmd
  log_file="$(__brief_route)"
  if [ -z "${log_file}" ] || [ "${log_file}" = "${__brief_default}" ] || ! command -v tee >/dev/null 2>&1; then
    command "${bin_name}" "$@"
    return $?
  fi

  start_pwd="${PWD}"
  launch_cmd="$(__brief_build_cmdline "${bin_name}" "$@")"
  __brief_append "from shell" 0 "${PWD}" "${launch_cmd}"
  __BRIEF_SKIP_NEXT_REMOTE_HIST=1

  transcript="$(mktemp "${__brief_base}/tmp/nc.transcript.XXXXXX")" || {
    command "${bin_name}" "$@"
    return $?
  }
  stdin_log="$(mktemp "${__brief_base}/tmp/nc.stdin.XXXXXX")" || {
    command "${bin_name}" "$@"
    rm -f "${transcript}" >/dev/null 2>&1 || true
    return $?
  }

  used_script=0
  if command -v script >/dev/null 2>&1; then
    run_cmd="$(printf '%q ' "${bin_name}" "$@")"
    run_cmd="${run_cmd% }"

    if script --help 2>&1 | grep -q -- '--log-in'; then
      command script -q -e -f --log-in "${stdin_log}" --log-out "${transcript}" -c "${run_cmd}"
      nc_rc=$?
      if [ -s "${stdin_log}" ] || [ -s "${transcript}" ]; then
        used_script=1
      fi
    fi

    if [ "${used_script}" = "0" ] && script --help 2>&1 | grep -q -- '-I'; then
      command script -q -e -f -I "${stdin_log}" -O "${transcript}" -c "${run_cmd}"
      nc_rc=$?
      if [ -s "${stdin_log}" ] || [ -s "${transcript}" ]; then
        used_script=1
      fi
    fi
  fi

  if [ "${used_script}" = "0" ]; then
    case "${bin_name}" in
      nc|ncat|netcat|socat|rlwrap)
        command "${bin_name}" "$@" 2>&1 | tee -a "${transcript}"
        nc_rc="${PIPESTATUS[0]}"
        ;;
      *)
        command "${bin_name}" "$@"
        nc_rc=$?
        ;;
    esac
  fi

  output_count="$(__brief_parse_remote_output_commands "${transcript}" "${start_pwd}" "${source_label}")"

  allow_input_fallback=0
  case "${bin_name}" in
    nc|ncat|netcat|socat|rlwrap)
      allow_input_fallback=1
      ;;
  esac

  if [ "${allow_input_fallback}" = "1" ] && [ "${output_count:-0}" = "0" ] && [ -s "${stdin_log}" ]; then
    __brief_capture_remote_input_commands "${stdin_log}" "${start_pwd}" "${source_label}" >/dev/null
  fi

  rm -f "${transcript}" >/dev/null 2>&1 || true
  rm -f "${stdin_log}" >/dev/null 2>&1 || true
  return "${nc_rc}"
}

# Force our wrappers even if shell has aliases like `alias nc='rlwrap nc'`.
unalias nc 2>/dev/null || true
unalias ncat 2>/dev/null || true
unalias netcat 2>/dev/null || true
unalias ssh 2>/dev/null || true
unalias telnet 2>/dev/null || true
unalias socat 2>/dev/null || true
unalias rlwrap 2>/dev/null || true
unalias ftp 2>/dev/null || true
unalias sftp 2>/dev/null || true
unalias rlogin 2>/dev/null || true
unalias rsh 2>/dev/null || true

nc() { __brief_remote_wrapper nc "from nc" "$@"; }
ncat() { __brief_remote_wrapper ncat "from ncat" "$@"; }
netcat() { __brief_remote_wrapper netcat "from netcat" "$@"; }
ssh() { __brief_remote_wrapper ssh "from ssh" "$@"; }
telnet() { __brief_remote_wrapper telnet "from telnet" "$@"; }
socat() { __brief_remote_wrapper socat "from socat" "$@"; }
rlwrap() { __brief_remote_wrapper rlwrap "from rlwrap" "$@"; }
ftp() { __brief_remote_wrapper ftp "from ftp" "$@"; }
sftp() { __brief_remote_wrapper sftp "from sftp" "$@"; }
rlogin() { __brief_remote_wrapper rlogin "from rlogin" "$@"; }
rsh() { __brief_remote_wrapper rsh "from rsh" "$@"; }

if [ -n "${ZSH_VERSION:-}" ]; then
  typeset -ga precmd_functions 2>/dev/null || true
  case " ${precmd_functions[*]:-} " in
    *" __brief_log_last "*) ;;
    *) precmd_functions+=(__brief_log_last) ;;
  esac
else
  if [ -n "${PROMPT_COMMAND:-}" ]; then
    case ";${PROMPT_COMMAND};" in
      *";__brief_log_last;"*) ;;
      *) PROMPT_COMMAND="__brief_log_last; ${PROMPT_COMMAND}" ;;
    esac
  else
    PROMPT_COMMAND="__brief_log_last"
  fi
fi

export __BRIEF_HOOK_LOADED=1
"""
    SHELL_RCFILE.write_text(rc, encoding="utf-8", errors="ignore")

def _ensure_bashrc_hook():
    ensure_dirs()
    shell_hook = (
        f'{HOOK_BEGIN}\n'
        f'if [ -f "{SHELL_RCFILE}" ]; then\n'
        f'  source "{SHELL_RCFILE}" > /dev/null 2>&1\n'
        "fi\n"
        f"{HOOK_END}\n"
    )
    content = BASHRC_FILE.read_text(encoding="utf-8", errors="ignore") if BASHRC_FILE.exists() else ""
    block_re = re.compile(rf"{re.escape(HOOK_BEGIN)}.*?{re.escape(HOOK_END)}\n?", re.S)
    if block_re.search(content):
        updated = block_re.sub(shell_hook, content, count=1)
    else:
        prefix = "" if not content or content.endswith("\n") else "\n"
        updated = f"{content}{prefix}\n{shell_hook}"
    BASHRC_FILE.write_text(updated, encoding="utf-8", errors="ignore")

def _ensure_default_route():
    if not CURRENT_SESSION_FILE.exists():
        CURRENT_SESSION_FILE.write_text(DEVNULL_ROUTE, encoding="utf-8")
        return
    current = CURRENT_SESSION_FILE.read_text(encoding="utf-8", errors="ignore").strip()
    if not current:
        CURRENT_SESSION_FILE.write_text(DEVNULL_ROUTE, encoding="utf-8")

def _ensure_global_logger():
    ensure_dirs()
    _require_recording_tools()
    _write_shell_rcfile()
    _ensure_bashrc_hook()
    _ensure_default_route()

def _recording_active():
    """Recording is active when current route points to a real session file."""
    if not CURRENT_SESSION_FILE.exists():
        return None
    log_path = CURRENT_SESSION_FILE.read_text(errors="ignore").strip()
    if not log_path or log_path == DEVNULL_ROUTE:
        return None
    log_file = Path(log_path)
    return log_file if log_file.exists() else None

def set_current_session(log_file):
    CURRENT_SESSION_FILE.write_text(str(log_file), encoding="utf-8")

def set_null_route():
    CURRENT_SESSION_FILE.write_text(DEVNULL_ROUTE, encoding="utf-8")

def _read_current_session_meta():
    try:
        if CURRENT_SESSION_META_FILE.exists():
            return json.loads(CURRENT_SESSION_META_FILE.read_text(errors="ignore") or "{}")
    except (OSError, json.JSONDecodeError):
        return None
    return None

def _write_current_session_meta(meta: dict):
    CURRENT_SESSION_META_FILE.write_text(json.dumps(meta, indent=2, sort_keys=True))

def _clear_current_session_meta():
    CURRENT_SESSION_META_FILE.unlink(missing_ok=True)

def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def _supports_unicode():
    encoding = (sys.stdout.encoding or "").lower()
    return "utf" in encoding

def _box_chars():
    if _supports_unicode():
        return "┌", "┐", "└", "┘", "─", "│"
    return "+", "+", "+", "+", "-", "|"

def _arrow():
    return "→" if _supports_unicode() else "->"

def _warn_symbol():
    return "⚠" if _supports_unicode() else "!"

def box_string(lines, width=None):
    inner_width = _clamp_width(width or BOX_INNER_WIDTH)
    tl, tr, bl, br, h, v = _box_chars()
    top = f"{tl}{h * inner_width}{tr}"
    bottom = f"{bl}{h * inner_width}{br}"
    out = [top]
    for line in lines:
        wrapped = textwrap.wrap(
            line,
            width=inner_width,
            replace_whitespace=False,
            drop_whitespace=False,
        ) if line else [""]
        for w in wrapped:
            out.append(f"{v}{w.ljust(inner_width)}{v}")
    out.append(bottom)
    return "\n".join(out)

def _terminal_width():
    try:
        return shutil.get_terminal_size().columns
    except OSError:
        return 80

def _clamp_width(width):
    term = _terminal_width()
    return max(40, min(width, term - 2))

def print_box(lines, width=None):
    print()
    print(box_string(lines, width))

def check_hf_token():
    if "HF_TOKEN" not in os.environ or not os.environ["HF_TOKEN"].strip():
        arrow = _arrow()
        warn = _warn_symbol()
        lines = [
            f"{warn}  Hugging Face API token not found",
            "",
            f"{arrow} Get a token:",
            "  https://huggingface.co/settings/tokens",
            "",
            f"{arrow} Steps:",
            "  1. Click \"New token\"",
            "  2. Select \"Read\"",
            "  3. Click \"Create Token\"",
            "",
            f"{arrow} Then run:",
            "  export HF_TOKEN=hf_xxxxxxxxxxxxxxxxx",
        ]
        print_box(lines)
        sys.exit(2)

def get_client():
    check_hf_token()
    try:
        from openai import OpenAI
    except ImportError:
        print("[-] Python package 'openai' is not installed for this runtime.")
        print("[!] Run: ./requirements.sh")
        sys.exit(2)
    return OpenAI(
        base_url=HF_BASE_URL,
        api_key=os.environ["HF_TOKEN"]
    )

# =========================
# SESSION RECORDING
# =========================

def start_session():
    ensure_dirs()
    if not _is_linux():
        print("[-] Recording backend uses bash hooks; this platform is not Linux.")
        sys.exit(2)
    _ensure_global_logger()
    active_log = _recording_active()
    if active_log:
        print(f"[-] Recording is already active: {active_log}")
        print("[!] Stop it first with: brief --stop")
        sys.exit(1)

    name = input("Session name: ").strip()
    if not name:
        print("[-] Session name required")
        sys.exit(1)

    log_file = SESS_DIR / f"{name}.md"
    if log_file.exists():
        print("[-] file name alredy exist")
        print(f"[!] if you want to save history in same file then do this 'brief --use {log_file}'")
        sys.exit(1)

    set_current_session(log_file)
    _write_current_session_meta(
        {
            "log_file": str(log_file),
            "session_name": name,
            "backend": "global-shell-hook",
            "route": "session-file",
            "started_at": utc_now(),
        }
    )
    with open(log_file, "w", encoding="utf-8", errors="ignore") as f:
        f.write(f"# command log created By Brief at {utc_now()}\n")
        f.write("\n")
        f.write("# Brief is a command-line tool it records your terminal activity during CTF challenges or lab exercises and leverages AI to produce a structured, in-depth report.\n\n")
    print("[+] Recording session started")
    print(f"[+] Session file: {log_file}")

# =========================
# USE EXISTING SESSION
# =========================

def _next_terminal_index(log_file):
    try:
        # Attachments are logical segments in the same session file.
        content = log_file.read_text(errors="ignore").splitlines()
    except FileNotFoundError:
        return 1
    attached = sum(1 for line in content if line.startswith("# attached"))
    return max(1, attached + 1)

def use_session(path):
    ensure_dirs()
    if not _is_linux():
        print("[-] Recording backend uses bash hooks; this platform is not Linux.")
        sys.exit(2)
    _ensure_global_logger()
    active_log = _recording_active()
    if active_log:
        print(f"[-] Recording is already active: {active_log}")
        print("[!] Stop it first with: brief --stop")
        sys.exit(1)

    log_file = _resolve_session_path(path)

    if not log_file.exists():
        print("[-] File not found")
        sys.exit(1)

    set_current_session(log_file)
    term_index = _next_terminal_index(log_file)
    _write_current_session_meta(
        {
            "log_file": str(log_file),
            "session_name": log_file.stem,
            "backend": "global-shell-hook",
            "route": "session-file",
            "started_at": utc_now(),
        }
    )
    with open(log_file, "a", encoding="utf-8", errors="ignore") as f:
        f.write(f"\n# attached {term_index} at {utc_now()}\n\n")
    print("[+] Recording continued in existing session")
    print(f"[+] Session file: {log_file}")

# =========================
# STOP SESSION
# =========================

def stop_session():
    ensure_dirs()
    if not _is_linux():
        print("[-] Recording backend uses bash hooks; this platform is not Linux.")
        sys.exit(2)
    _ensure_global_logger()
    meta = _read_current_session_meta() or {}
    log_path = CURRENT_SESSION_FILE.read_text(errors="ignore").strip() if CURRENT_SESSION_FILE.exists() else ""
    log_file = None
    if log_path and log_path != DEVNULL_ROUTE:
        log_file = Path(meta.get("log_file") or log_path)

    if not log_file:
        print("[-] There is No active session to stop.")
        sessions = sorted(SESS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
        if sessions:
            print(f"[+] most resent session is alredy stoped and saved here {sessions[0]}")
        else:
            print("[+] no saved session found.")
        return

    session_name = log_file.stem if log_file else "session"

    set_null_route()
    _clear_current_session_meta()

    print(f"[+] Brief is stopped and session file is stored here {log_file}")
    print("to create methodology (AARB) report do this")
    print(f"brief -i {log_file}")

# =========================
# ACTIVE SESSION
# =========================

def active_session(target=None):
    ensure_dirs()
    if not _is_linux():
        print("[-] Recording backend uses bash hooks; this platform is not Linux.")
        sys.exit(2)
    _ensure_global_logger()

    if target and target.lower() != "session":
        print("[-] Invalid argument for --active")
        print("[!] Use: brief --active session")
        sys.exit(2)

    meta = _read_current_session_meta() or {}
    active_log = _recording_active()

    if not active_log:
        print("[-] No active session.")
        print("[+] Start session with 'brief --start'")
        return

    started_at = meta.get("started_at", "unknown")
    print("[+] Active session is running")
    print(f"[+] Session file: {active_log}")
    print(f"[+] Started at: {started_at}")

# =========================
# LIST
# =========================

def list_sessions():
    ensure_dirs()
    files = sorted(SESS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not files:
        print("[*] No sessions found")
        return
    for session_file in files:
        print(str(session_file))

def list_reports():
    ensure_dirs()
    reports = sorted(
        OUT_DIR.glob("*.analysis.*"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    if not reports:
        print("[*] No reports found")
        return
    for report in reports:
        print(str(report))

def _resolve_session_path(arg: str) -> Path:
    """
    Accept either a full path to a session file or a bare session name (without .md),
    and return the resolved Path.
    """
    p = Path(arg)
    if p.is_absolute() or p.parent != Path(".") or arg.endswith(".md"):
        return p
    return SESS_DIR / f"{arg}.md"

# =========================
# TAIL
# =========================

def tail_latest_session(lines=20):
    ensure_dirs()
    files = sorted(SESS_DIR.glob("*.md"))
    if not files:
        print("[*] No sessions found")
        return
    latest = max(files, key=lambda p: p.stat().st_mtime)
    content = latest.read_text(errors="ignore").splitlines()
    for line in content[-lines:]:
        print(line)

# =========================
# INGEST
# =========================

def ingest_session(path):
    ensure_dirs()
    path = _resolve_session_path(path)

    if not path.exists():
        print("[-] File not found")
        sys.exit(1)

    check_hf_token()

    session_text = path.read_text(errors="ignore")
    prompt = PROMPT_TEMPLATE.replace("{{SESSION}}", session_text)

    result = {"completion": None, "error": None}
    done_event = threading.Event()

    def request_worker():
        try:
            client = get_client()
            result["completion"] = client.chat.completions.create(
                model=MODEL,
                messages=[{"role": "user", "content": prompt}],
            )
        except Exception as exc:
            result["error"] = exc
        finally:
            done_event.set()

    request_thread = threading.Thread(target=request_worker, daemon=True)
    request_thread.start()

    print("[-] wait for second report is on the way...")
    stages = [
        "[+] Starting report generation",
        "[+] Ingesting data",
        "[+] Parsing logs",
        "[+] Correlating events",
        "[+] Rendering output",
    ]
    stage_index = 0
    next_stage_at = time.monotonic()
    spinner_frames = ["|", "/", "-", "\\"]
    spinner_index = 0
    warned_extra = False
    started_at = time.monotonic()

    while not done_event.is_set():
        now = time.monotonic()
        if stage_index < len(stages) and now >= next_stage_at:
            print(stages[stage_index])
            stage_index += 1
            next_stage_at = now + 6
        if not warned_extra and (now - started_at) >= 180:
            print("[+] Ingesting data 30 sec more.")
            warned_extra = True
        sys.stdout.write(f"\r[-] {spinner_frames[spinner_index]} ")
        sys.stdout.flush()
        spinner_index = (spinner_index + 1) % len(spinner_frames)
        time.sleep(0.2)

    request_thread.join()
    sys.stdout.write("\r" + (" " * 20) + "\r")
    sys.stdout.flush()

    if result["error"] is not None:
        print(f"[-] {result['error']}")
        sys.exit(1)

    print("[+] Report generated successfully")
    completion = result["completion"]

    output = completion.choices[0].message.content
    out_file = OUT_DIR / f"{path.stem}.analysis.md"
    out_file.write_text(output)

    # Create HTML file with embedded markdown (properly escaped)
    html_file = OUT_DIR / f"{path.stem}.analysis.html"
    
    # Escape the markdown content for safe JSON embedding
    markdown_json = json.dumps(output)
    
    html_content = HTML_TEMPLATE.replace("{{MARKDOWN_JSON}}", markdown_json)
    html_file.write_text(html_content)

    lines = [
        "[+] Analysis written to:",
        f"  {out_file}",
        "",
        "[+] HTML report generated:",
        f"  {html_file}",
        "",
        "[✓] REPORT READY",
        "",
        "Open in browser:",
        f"  {html_file}",
        "",
        "Or run:",
        f"  firefox {html_file}",
        f"  google-chrome {html_file}",
    ]
    box_width = max(BOX_INNER_WIDTH, max((len(l) for l in lines if l), default=BOX_INNER_WIDTH))
    print_box(lines, width=box_width)

def ingest_latest_session():
    ensure_dirs()
    sessions = sorted(SESS_DIR.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True)

    if not sessions:
        print("[-] No sessions found")
        sys.exit(1)

    latest = sessions[0]
    print(f"[+] Using latest session: {latest.name}")
    ingest_session(latest)

# =========================
# CLI
# =========================

def help_text():
    return """brief - Sharpen your pentest methodology.

Syntax: brief [--version] (--start | --use SESSION_FILE | --list | --reports | --tail [N] | --ingest SESSION_FILE | --latest | --active session | --stop)

Options:
  -h, --help                       show this help message and exit.
  -v, --version                    show program version and exit.
  -s, --start                      start a new command recording session.
  -u, --use SESSION_FILE           continue recording in an existing session file.
  -l, --list                       print full paths of all saved session files.
  -r, --reports                    print full paths of all generated report files.
  -i, --ingest SESSION_FILE        analyze a specific session file.
  -la, --latest                    analyze the most recent session.
  -as, --active session            show currently active (not stopped) session.
  -st, --stop                      stop recording for the current session.
  -t [N], --tail [N]               print last N lines of the most recent session (default: 20).

Environment:
  HF_TOKEN                        Hugging Face API token (required for analysis)

Brief:
  `brief --start`                 begins a new session.
  `brief --use <session file>`    continues an existing session.
  `brief --stop`                  stops the active session.
  `brief --list`                  show all saved session files.
  `brief --reports`               show all saved generated reports.

Examples:
  brief --start
  brief --list
  brief --reports
  brief --tail 50
  brief --use /home/parrot/.brief/sessions/cap.md
  brief --latest
  brief --active session
  brief --ingest /home/parrot/.brief/sessions/cap.md
  brief --stop
"""

class BriefArgumentParser(argparse.ArgumentParser):
    def format_help(self):
        return help_text()

    def error(self, message):
        if "unrecognized arguments" in message:
            message = f"{message}\nHint: use --ingest or -i to analyze a session file."
        super().error(message)

def main():
    parser = BriefArgumentParser(
        prog="brief",
        description=(
            "Record CTF / lab command history and generate a detailed post‑mortem analysis. "
            "Command capture uses a global bash hook across terminals. "
            "Use one action per run: start a new session, reuse a session file, list sessions, "
            "tail the most recent session, or analyze a session."
        ),
        epilog=(
            "Examples (what each command does):\n"
            "  brief --start                    -> start a new recording session\n"
            "  brief --list                     -> print all saved session file paths\n"
            "  brief --reports                  -> print all generated report file paths\n"
            "  brief --tail 50                  -> print the last 50 lines of the recent session\n"
            "  brief --use (brief --list)       -> continue recording in the latest session file\n"
            "  brief --use ladder.md            -> continue recording in ladder.md\n"
            "  brief --latest                   -> analyze the most recent session\n"
            "  brief --active session           -> show currently active session\n"
            "  brief --ingest ladder.md         -> analyze a specific session file\n"
            "  brief --stop                     -> stop recording for active session\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("-v", "--version", action="version", version=f"brief {VERSION}")

    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument("-s", "--start", action="store_true", help="start a new command recording session")
    group.add_argument("-u", "--use", metavar="SESSION_FILE", help="continue recording in an existing session file")
    group.add_argument("-l", "--list", action="store_true", help="print full paths of all saved session files")
    group.add_argument("-r", "--reports", action="store_true", help="print full paths of all generated report files")
    group.add_argument("-t", "--tail", nargs="?", const=20, type=int, metavar="N", help="print the last N lines of the most recent session (default: 20)")
    group.add_argument("-i", "--ingest", metavar="SESSION_FILE", help="analyze a specific session file")
    group.add_argument("-la", "--latest", action="store_true", help="analyze the most recent session")
    group.add_argument("-as", "--active", nargs="?", const="session", metavar="session", help="show currently active (not stopped) session")
    group.add_argument("-st", "--stop", action="store_true", help="stop recording for the current session")

    args = parser.parse_args()

    if args.start:
        start_session()
    elif args.use:
        use_session(args.use)
    elif args.list:
        list_sessions()
    elif args.reports:
        list_reports()
    elif args.tail is not None:
        tail_latest_session(args.tail)
    elif args.ingest:
        ingest_session(args.ingest)
    elif args.latest:
        ingest_latest_session()
    elif args.active is not None:
        active_session(args.active)
    elif args.stop:
        stop_session()

if __name__ == "__main__":main()

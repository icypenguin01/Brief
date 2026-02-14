#!/usr/bin/env python3

import os
import argparse
import subprocess
import time
import threading
import textwrap
import shutil
from pathlib import Path
from datetime import datetime, timezone
from openai import OpenAI
import sys
import json

# =========================
# VERSION
# =========================

VERSION = "1.0.0"

# =========================
# CONFIG
# =========================

BASE_DIR = Path.home() / ".brief"
SESS_DIR = BASE_DIR / "sessions"
OUT_DIR = BASE_DIR / "outputs"
CURRENT_SESSION_FILE = BASE_DIR / ".current_session"
AUTO_ATTACH_HOOK = BASE_DIR / "autoattach.sh"
STOP_FILE = BASE_DIR / ".stop"

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
    SESS_DIR.mkdir(parents=True, exist_ok=True)
    OUT_DIR.mkdir(parents=True, exist_ok=True)

def set_current_session(log_file):
    CURRENT_SESSION_FILE.write_text(str(log_file))

def write_autoattach_hook():
    hook = f"""# brief auto-attach (source this in ~/.bashrc)
if [ -n "$BRIEF_AUTO_ATTACHED" ]; then return; fi
if [ ! -f "{CURRENT_SESSION_FILE}" ]; then return; fi
BRIEF_LOG_PATH="$(cat "{CURRENT_SESSION_FILE}")"
if [ -z "$BRIEF_LOG_PATH" ] || [ ! -f "$BRIEF_LOG_PATH" ]; then return; fi
if [ -f "{STOP_FILE}" ]; then return; fi

BRIEF_TERM_LABEL="$(awk '/^# terminal /{{print $3}}' "$BRIEF_LOG_PATH" | tail -n 1)"
if [ -z "$BRIEF_TERM_LABEL" ]; then
  BRIEF_TERM_LABEL=1
else
  BRIEF_TERM_LABEL=$((BRIEF_TERM_LABEL + 1))
fi

TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
echo "# terminal $BRIEF_TERM_LABEL started $TS" >> "$BRIEF_LOG_PATH"

export BRIEF_LOG="$BRIEF_LOG_PATH"
export BRIEF_TERM_LABEL="$BRIEF_TERM_LABEL"
export BRIEF_AUTO_ATTACHED=1

set +o history
shopt -s histappend
HISTCONTROL=

__brief_log() {{
  RET=$?;
  CMD=$(history 1 | sed "s/^ *[0-9]\\+ *//");
  [ -z "$CMD" ] && return;
  if [ -f "{STOP_FILE}" ]; then return; fi
  if [ -z "$BRIEF_LOG" ] || [ ! -f "$BRIEF_LOG" ]; then return; fi
  case "$CMD" in
    PROMPT_COMMAND=__brief_log*|*__brief_log*|history\\ -c* ) return ;;
  esac
  if [ "$CMD" = "$BRIEF_LAST_CMD" ]; then return; fi;
  BRIEF_LAST_CMD="$CMD";
  TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ");
  CWD=$(pwd);
  TERM_LABEL=${{BRIEF_TERM_LABEL:-1}};
  echo -e "$TS\\t$RET\\t$CWD\\t[from terminal $TERM_LABEL] $CMD" >> "$BRIEF_LOG";
}}

if [[ "$PROMPT_COMMAND" != *"__brief_log"* ]]; then
  if [ -n "$PROMPT_COMMAND" ]; then
    PROMPT_COMMAND="__brief_log; $PROMPT_COMMAND"
  else
    PROMPT_COMMAND="__brief_log"
  fi
fi
set -o history
"""
    AUTO_ATTACH_HOOK.write_text(hook)

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
    return OpenAI(
        base_url=HF_BASE_URL,
        api_key=os.environ["HF_TOKEN"]
    )

# =========================
# SESSION RECORDING
# =========================

def start_session():
    ensure_dirs()
    write_autoattach_hook()
    STOP_FILE.unlink(missing_ok=True)

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
    with open(log_file, "w") as f:
        f.write(f"# ctf command log created {utc_now()}\n")
        f.write(f"# terminal 1 started {utc_now()}\n\n")

    rcfile = BASE_DIR / ".brief_bashrc"
    rcfile.write_text(
        "if [ -f ~/.bashrc ]; then source ~/.bashrc; fi\n"
        "set +o history\n"
        "shopt -s histappend\n"
        "HISTCONTROL=\n"
        "__brief_log() {\n"
        "  RET=$?;\n"
        "  CMD=$(history 1 | sed \"s/^ *[0-9]\\+ *//\");\n"
        "  [ -z \"$CMD\" ] && return;\n"
        f"  if [ -f \"{STOP_FILE}\" ]; then return; fi;\n"
        "  if [ -z \"$BRIEF_LOG\" ] || [ ! -f \"$BRIEF_LOG\" ]; then return; fi;\n"
        "  case \"$CMD\" in\n"
        "    PROMPT_COMMAND=__brief_log*|*__brief_log*|history\\ -c* ) return ;;\n"
        "  esac\n"
        "  if [ \"$CMD\" = \"$BRIEF_LAST_CMD\" ]; then return; fi;\n"
        "  BRIEF_LAST_CMD=\"$CMD\";\n"
        "  TS=$(date -u +\"%Y-%m-%dT%H:%M:%SZ\");\n"
        "  CWD=$(pwd);\n"
        "  TERM_LABEL=${BRIEF_TERM_LABEL:-1};\n"
        "  echo -e \"$TS\\t$RET\\t$CWD\\t[from terminal $TERM_LABEL] $CMD\" >> \"$BRIEF_LOG\";\n"
        "}\n"
        "PROMPT_COMMAND=__brief_log\n"
        "set -o history\n"
        "history -c\n"
    )

    env = os.environ.copy()
    env["BRIEF_LOG"] = str(log_file)
    env["BRIEF_TERM_LABEL"] = "1"

    print("[+] Recording session (type `brief --stop` to stop; enter from any terminal or tab)\n")
    subprocess.run(["bash", "--rcfile", str(rcfile)], env=env)

    with open(log_file, "a") as f:
        f.write(f"# terminal 1 ended {utc_now()}\n")

    rcfile.unlink(missing_ok=True)
    if STOP_FILE.exists():
        print(f"[+] Recording already stopped for this {log_file.stem}")
        print(f"[+] Session file: {log_file}")
    else:
        print(f"[*] Terminal closed. Recording still active for {log_file.stem}.")

# =========================
# USE EXISTING SESSION
# =========================

def _next_terminal_index(log_file):
    term_index = 1
    try:
        for line in log_file.read_text(errors="ignore").splitlines():
            if line.startswith("# terminal "):
                parts = line.split()
                if len(parts) >= 3 and parts[2].isdigit():
                    term_index = max(term_index, int(parts[2]))
    except FileNotFoundError:
        return 1
    return term_index + 1

def use_session(path):
    ensure_dirs()
    write_autoattach_hook()
    STOP_FILE.unlink(missing_ok=True)
    log_file = Path(path)

    if not log_file.exists():
        print("[-] File not found")
        sys.exit(1)

    set_current_session(log_file)
    term_index = _next_terminal_index(log_file)
    with open(log_file, "a") as f:
        f.write(f"# terminal {term_index} started {utc_now()}\n")

    rcfile = BASE_DIR / ".brief_bashrc"
    rcfile.write_text(
        "if [ -f ~/.bashrc ]; then source ~/.bashrc; fi\n"
        "set +o history\n"
        "shopt -s histappend\n"
        "HISTCONTROL=\n"
        "__brief_log() {\n"
        "  RET=$?;\n"
        "  CMD=$(history 1 | sed \"s/^ *[0-9]\\+ *//\");\n"
        "  [ -z \"$CMD\" ] && return;\n"
        f"  if [ -f \"{STOP_FILE}\" ]; then return; fi;\n"
        "  if [ -z \"$BRIEF_LOG\" ] || [ ! -f \"$BRIEF_LOG\" ]; then return; fi;\n"
        "  case \"$CMD\" in\n"
        "    PROMPT_COMMAND=__brief_log*|*__brief_log*|history\\ -c* ) return ;;\n"
        "  esac\n"
        "  if [ \"$CMD\" = \"$BRIEF_LAST_CMD\" ]; then return; fi;\n"
        "  BRIEF_LAST_CMD=\"$CMD\";\n"
        "  TS=$(date -u +\"%Y-%m-%dT%H:%M:%SZ\");\n"
        "  CWD=$(pwd);\n"
        "  TERM_LABEL=${BRIEF_TERM_LABEL:-1};\n"
        "  echo -e \"$TS\\t$RET\\t$CWD\\t[from terminal $TERM_LABEL] $CMD\" >> \"$BRIEF_LOG\";\n"
        "}\n"
        "PROMPT_COMMAND=__brief_log\n"
        "set -o history\n"
        "history -c\n"
    )

    env = os.environ.copy()
    env["BRIEF_LOG"] = str(log_file)
    env["BRIEF_TERM_LABEL"] = str(term_index)

    print(f"[+] Using existing session (terminal {term_index}) (type `brief --stop` to stop; enter from any terminal or tab)\n")
    subprocess.run(["bash", "--rcfile", str(rcfile)], env=env)

    with open(log_file, "a") as f:
        f.write(f"# terminal {term_index} ended {utc_now()}\n")

    rcfile.unlink(missing_ok=True)
    if STOP_FILE.exists():
        print(f"[+] Recording already stopped for this {log_file.stem}")
        print(f"[+] Session file: {log_file}")
    else:
        print(f"[*] Terminal closed. Recording still active for {log_file.stem}.")

# =========================
# STOP SESSION
# =========================

def stop_session():
    ensure_dirs()
    if not CURRENT_SESSION_FILE.exists():
        latest = None
        files = sorted(SESS_DIR.glob("*.md"))
        if files:
            latest = max(files, key=lambda p: p.stat().st_mtime)
        if latest:
            print(f"[-] No session to stop. Most recent session '{latest.stem}' already stopped.")
        else:
            print("[-] No session to stop. No sessions found.")
        return

    STOP_FILE.write_text(utc_now())

    log_path = CURRENT_SESSION_FILE.read_text(errors="ignore").strip()
    log_file = Path(log_path) if log_path else None

    term_label = os.environ.get("BRIEF_TERM_LABEL")
    if log_file and log_file.exists() and term_label:
        with open(log_file, "a") as f:
            f.write(f"# terminal {term_label} ended {utc_now()}\n")

    CURRENT_SESSION_FILE.unlink(missing_ok=True)

    session_name = log_file.stem if log_file else "session"
    print(f"[+] Recording stopped for this {session_name}")
    if log_file:
        print(f"[+] Session file: {log_file}")

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
    path = Path(path)

    if not path.exists():
        print("[-] File not found")
        sys.exit(1)

    check_hf_token()

    session_text = path.read_text(errors="ignore")
    prompt = PROMPT_TEMPLATE.replace("{{SESSION}}", session_text)

    stop_event = threading.Event()
    progress_started = {"value": False}

    def progress_bar():
        time.sleep(0.4)
        if stop_event.is_set():
            return
        progress_started["value"] = True
        print("[*] Ingesting data...")
        for pct in range(0, 101, 10):
            if stop_event.is_set():
                break
            bar = "#" * (pct // 10) + "-" * (10 - (pct // 10))
            sys.stdout.write(f"\r    [{bar}] {pct}%")
            sys.stdout.flush()
            if pct < 100:
                time.sleep(1)
        if progress_started["value"]:
            print()

    progress_thread = threading.Thread(target=progress_bar, daemon=True)
    progress_thread.start()

    client = get_client()
    completion = client.chat.completions.create(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
    )
    stop_event.set()
    progress_thread.join()

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

Syntax: brief [--version] (--start | --use SESSION_FILE | --list | --tail [N] | --ingest SESSION_FILE | --latest | --stop)

Options:
  -h, --help                      show this help message and exit
  --version                       show program version and exit
  --start                         start a new command recording session
  -u, --use SESSION_FILE          append a new terminal history to an existing session file
  -l, --list                      print full paths of all saved session files
  --tail [N]                      print last N lines of the most recent session (default: 20)
  -i, --ingest SESSION_FILE       analyze a specific session file
  --latest                        analyze the most recent session
  --stop                          stop recording the current session

Environment:
  HF_TOKEN                        Hugging Face API token (required for analysis)

Examples:
  brief --start
  brief --list
  brief --tail 50
  brief --use /home/parrot/.brief/sessions/cap.md
  brief --latest
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
            "Use one action per run: start a new session, reuse a session file, list the "
            "current session, tail its recent commands, or analyze a session."
        ),
        epilog=(
            "Examples (what each command does):\n"
            "  brief --start                    -> start a new recording session\n"
            "  brief --list                     -> print all saved session file paths\n"
            "  brief --tail 50                  -> print the last 50 lines of the recent session\n"
            "  brief --use (brief --list)       -> attach a new terminal to the latest session\n"
            "  brief --use ladder.md            -> attach a new terminal to ladder.md\n"
            "  brief --latest                   -> analyze the most recent session\n"
            "  brief --ingest ladder.md         -> analyze a specific session file\n"
            "  brief --stop                     -> stop recording in this shell\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("--version", action="version", version=f"brief {VERSION}")

    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument("--start", action="store_true", help="start a new command recording session")
    group.add_argument("-u", "--use", metavar="SESSION_FILE", help="append a new terminal's history to an existing session file")
    group.add_argument("-l", "--list", action="store_true", help="print full paths of all saved session files")
    group.add_argument("--tail", nargs="?", const=20, type=int, metavar="N", help="print the last N lines of the most recent session (default: 20)")
    group.add_argument("-i", "--ingest", metavar="SESSION_FILE", help="analyze a specific session file")
    group.add_argument("--latest", action="store_true", help="analyze the most recent session")
    group.add_argument("--stop", action="store_true", help="stop recording the current session")

    args = parser.parse_args()

    if args.start:
        start_session()
    elif args.use:
        use_session(args.use)
    elif args.list:
        list_sessions()
    elif args.tail is not None:
        tail_latest_session(args.tail)
    elif args.ingest:
        ingest_session(args.ingest)
    elif args.latest:
        ingest_latest_session()
    elif args.stop:
        stop_session()

if __name__ == "__main__":
    main()

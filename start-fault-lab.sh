#!/usr/bin/env bash
# One-click launcher for Fault Lab (Linux / macOS).
#
#   ./start-fault-lab.sh
#   ./start-fault-lab.sh --port 9000 --control-token my-secret --no-browser
#   ./start-fault-lab.sh --dev
#
# Set FAULT_LAB_PYTHON to a python interpreter to skip virtualenv creation.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PORT=8090
DEV=0
NO_BUILD=0
NO_BROWSER=0
REINSTALL=0
TOKEN=""
DIAG=""
LOG_LEVEL="info"

while [ $# -gt 0 ]; do
  case "$1" in
    --port) PORT="$2"; shift 2 ;;
    --control-token) TOKEN="$2"; shift 2 ;;
    --diagnostics-token) DIAG="$2"; shift 2 ;;
    --log-level) LOG_LEVEL="$2"; shift 2 ;;
    --dev) DEV=1; shift ;;
    --no-build) NO_BUILD=1; shift ;;
    --no-browser) NO_BROWSER=1; shift ;;
    --reinstall) REINSTALL=1; shift ;;
    -h|--help) sed -n '2,12p' "$0"; exit 0 ;;
    *) echo "unknown option: $1" >&2; exit 2 ;;
  esac
done

step() { printf '\n==> %s\n' "$1"; }
warn() { printf '!! %s\n' "$1"; }
ok()   { printf '   %s\n' "$1"; }

random_token() {
  LC_ALL=C tr -dc 'A-Za-z0-9' </dev/urandom | head -c 32 || true
}

[ -n "$TOKEN" ] || TOKEN="${SIMULATOR_CONTROL_TOKEN:-}"
if [ -z "$TOKEN" ]; then
  TOKEN="$(random_token)"
  warn "No control token given; generated a random one (shown below)."
fi

# --- backend virtualenv ------------------------------------------------------
if [ -n "${FAULT_LAB_PYTHON:-}" ]; then
  step "Using interpreter from FAULT_LAB_PYTHON"
  PY="$FAULT_LAB_PYTHON"
else
  step "Preparing backend environment"
  if [ "$REINSTALL" -eq 1 ]; then rm -rf "$ROOT/.venv"; fi
  if [ -x "$ROOT/.venv/bin/python" ]; then
    PY="$ROOT/.venv/bin/python"
    ok "Reusing existing virtualenv .venv"
  else
    command -v python3 >/dev/null 2>&1 || { echo "python3 not found; install Python 3.10+." >&2; exit 1; }
    ok "Creating virtualenv .venv"
    python3 -m venv "$ROOT/.venv"
    PY="$ROOT/.venv/bin/python"
    ok "Installing backend dependencies"
    "$PY" -m pip install --upgrade pip >/dev/null
    "$PY" -m pip install -e "$ROOT[dev]"
  fi
fi

# --- frontend ----------------------------------------------------------------
FRONTEND="$ROOT/frontend"
if [ "$DEV" -eq 1 ] || [ "$NO_BUILD" -eq 0 ]; then
  if command -v npm >/dev/null 2>&1; then
    if [ ! -d "$FRONTEND/node_modules" ] || [ "$REINSTALL" -eq 1 ]; then
      step "Installing frontend dependencies"
      ( cd "$FRONTEND" && npm install --no-audit --no-fund )
    fi
    if [ "$DEV" -eq 0 ] && { [ "$REINSTALL" -eq 1 ] || [ ! -f "$FRONTEND/dist/index.html" ]; }; then
      step "Building the console"
      ( cd "$FRONTEND" && npm run build )
    fi
  else
    if [ "$DEV" -eq 1 ]; then echo "npm not found; --dev needs Node.js." >&2; exit 1; fi
    warn "npm not found; skipping frontend build. Root path will show a build hint page."
  fi
fi

# --- environment -------------------------------------------------------------
export SIMULATOR_ADDR=":$PORT"
export SIMULATOR_CONTROL_TOKEN="$TOKEN"
export SIMULATOR_CONFIG_PATH="$ROOT/config/simulator.json"
export SIMULATOR_LOG_LEVEL="$LOG_LEVEL"
export PYTHONPATH="$ROOT/backend${PYTHONPATH:+:$PYTHONPATH}"
if [ -n "$DIAG" ]; then export SIMULATOR_DIAGNOSTICS_TOKEN="$DIAG"; fi

open_browser() {
  [ "$NO_BROWSER" -eq 1 ] && return 0
  ( sleep "$1"
    if command -v xdg-open >/dev/null 2>&1; then xdg-open "$2"
    elif command -v open >/dev/null 2>&1; then open "$2"
    fi ) >/dev/null 2>&1 &
}

if [ "$DEV" -eq 1 ]; then
  console_url="http://localhost:5173/"
else
  console_url="http://localhost:$PORT/"
fi

printf '\n----------------------------------------------\n'
printf ' Fault Lab starting\n'
printf '   Console        %s\n' "$console_url"
printf '   Liveness       http://localhost:%s/healthz\n' "$PORT"
printf '   Control token  %s\n' "$TOKEN"
[ -n "$DIAG" ] && printf '   Diagnostics    %s\n' "$DIAG"
printf ' Paste the control token into the console sign-in panel.\n'
printf ' Press Ctrl+C to stop.\n'
printf -- '----------------------------------------------\n'

# --- run ---------------------------------------------------------------------
if [ "$DEV" -eq 1 ]; then
  step "Starting backend (background) and Vite dev server (foreground)"
  ( cd "$ROOT" && exec "$PY" -m fault_lab.main ) &
  BACKEND_PID=$!
  trap 'kill "$BACKEND_PID" 2>/dev/null || true' EXIT
  open_browser 5 "http://localhost:5173/"
  ( cd "$FRONTEND" && exec npm run dev )
else
  open_browser 3 "$console_url"
  step "Starting Fault Lab backend (foreground)"
  cd "$ROOT"
  exec "$PY" -m fault_lab.main
fi

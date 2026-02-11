#!/usr/bin/env bash
# bootstrap.sh — Thin wrapper for installing claude-ctim.
# Usage:
#   curl -fsSL https://raw.githubusercontent.com/lounisbou/claude-ctim/main/scripts/bootstrap.sh | bash
#   ./scripts/bootstrap.sh
set -euo pipefail

APP_NAME="claude-ctim"
REPO_URL="https://github.com/lounisbou/claude-ctim.git"
MIN_PYTHON="3.11"

info()  { echo "  [INFO]  $*"; }
error() { echo "  [ERROR] $*" >&2; }

# Check Python version
check_python() {
    for cmd in python3.12 python3.11 python3 python; do
        if command -v "$cmd" &>/dev/null; then
            version=$("$cmd" -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
            major=$(echo "$version" | cut -d. -f1)
            minor=$(echo "$version" | cut -d. -f2)
            if [ "$major" -ge 3 ] && [ "$minor" -ge 11 ]; then
                PYTHON_CMD="$cmd"
                info "Found Python $version ($cmd)"
                return 0
            fi
        fi
    done
    return 1
}

# Detect if we're inside the cloned repo
detect_repo() {
    if [ -f "installer/main.py" ] && [ -f "pyproject.toml" ]; then
        REPO_DIR="$(pwd)"
        return 0
    fi
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]:-$0}")" && pwd)"
    if [ -f "$SCRIPT_DIR/../installer/main.py" ]; then
        REPO_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
        return 0
    fi
    return 1
}

echo ""
echo "=============================="
echo "  $APP_NAME Bootstrap"
echo "=============================="
echo ""

# Step 1: Find Python
if ! check_python; then
    error "Python $MIN_PYTHON+ is required but not found."
    if command -v brew &>/dev/null; then
        echo "  Install with: brew install python@3.12"
    elif command -v apt &>/dev/null; then
        echo "  Install with: sudo apt install python3.12 python3.12-venv"
    fi
    exit 1
fi

# Step 2: Find or clone repo
if detect_repo; then
    info "Found repo at: $REPO_DIR"
else
    REPO_DIR=$(mktemp -d)
    info "Cloning $APP_NAME to $REPO_DIR..."
    git clone --depth 1 "$REPO_URL" "$REPO_DIR"
fi

# Step 3: Hand off to Python installer
info "Starting installer..."
cd "$REPO_DIR"
exec "$PYTHON_CMD" -m installer.main "$@"

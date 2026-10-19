#!/usr/bin/env bash
# Forward to the Python installer, passing through all arguments.
set -euo pipefail
DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
exec python3 "${DIR}/install.py" "$@"

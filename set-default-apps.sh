#!/bin/bash
# Set default applications for file types using duti
# Usage: ./set-default-apps.sh
# Prerequisite: brew install duti

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DUTI_CONF="$SCRIPT_DIR/duti.conf"

if ! command -v duti &>/dev/null; then
  echo "duti not found. Installing..."
  brew install duti
fi

if [[ ! -f "$DUTI_CONF" ]]; then
  echo "Error: $DUTI_CONF not found"
  exit 1
fi

echo "Setting default applications from duti.conf..."
duti "$DUTI_CONF"
echo "Done."

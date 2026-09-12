#!/bin/sh
set -eu
exec python3 "$(dirname "$0")/build-display-60hz-candidate-dtb.py" "$@"

#!/usr/bin/env bash
set -eo pipefail
sorting_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
exec /usr/bin/python3 "$sorting_root/scripts/start_sorting_station.py" "$@"

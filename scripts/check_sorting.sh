#!/usr/bin/env bash
set -eo pipefail
sorting_check_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$sorting_check_root"
export PYTHONPATH="$sorting_check_root/src/sorting_station/hcr_sorting${PYTHONPATH:+:$PYTHONPATH}"
/usr/bin/python3 -m unittest discover -s tests -p test_sorting_launcher.py -v
/usr/bin/python3 -m unittest discover -s src/sorting_station/hcr_sorting/tests -p test_core.py -v
/usr/bin/python3 -m unittest discover -s src/sorting_station/hcr_sorting/tests -p test_modbus.py -v
/usr/bin/python3 -m unittest discover -s src/sorting_station/hcr -p test_zone_preview.py -v
for sorting_script in start_sorting.sh src/sorting_station/hcr/*.sh scripts/*.sh; do
  bash -n "$sorting_script"
done

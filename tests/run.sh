#!/bin/bash
# Runs every automated test: Python collector, then QML/JS logic.
set -eo pipefail
cd "$(dirname "$0")/.."
PYTHONPATH=collector python3 -m unittest discover -s tests -p 'test_*.py' "$@"
if [ -z "$OMAVIEW_SKIP_QML" ]; then
  QT_QPA_PLATFORM=offscreen /usr/lib/qt6/bin/qmltestrunner -input tests/qml -o -,txt 2>&1 | grep -E '^(FAIL|Totals|   (Actual|Expected|Loc))'
fi

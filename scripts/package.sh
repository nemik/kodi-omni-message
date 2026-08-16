#!/usr/bin/env bash
# Build the installable zip: dist/service.omnimessage-<version>.zip
#
# Kodi requires every path in the zip to sit under a single top-level folder
# named exactly like the add-on id, which is why we zip from the repo root.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ADDON_ID="service.omnimessage"
cd "$ROOT"

VERSION="$(python3 -c "
import xml.etree.ElementTree as ET
print(ET.parse('$ADDON_ID/addon.xml').getroot().get('version'))")"
if [[ -z "$VERSION" || "$VERSION" == "None" ]]; then
  echo "could not read version from $ADDON_ID/addon.xml" >&2
  exit 1
fi

ZIP="dist/$ADDON_ID-$VERSION.zip"
mkdir -p dist
rm -f "$ZIP"

zip -q -r -X "$ZIP" "$ADDON_ID" \
  -x '*__pycache__*' '*.pyc' '*.DS_Store' '*/.*'

echo "$ZIP"
unzip -Z1 "$ZIP" | sed 's/^/  /'

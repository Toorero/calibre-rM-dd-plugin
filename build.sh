#!/bin/bash

# SPDX-License-Identifier: EUPL-1.2

OUT="${OUT:-out}"
set -euxo pipefail
rm -rf ./calibre-rM-dd-driver-plugin.zip "$OUT"

mkdir "$OUT"
cp __init__.py config.py plugin-import-name-remarkable_rmapi_plugin.txt "$OUT"
pushd "$OUT"
# Include all the dependencies in the zip archive
zip -r ../calibre-rM-dd-driver-plugin.zip ./ -x ".*" "*.pyc"
popd

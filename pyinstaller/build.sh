#!/bin/bash -e

VERSION="0.3.1"
PREFIX="${HOME}/git/pyinstaller"

rm -rf build/ dist/ *.log

cd ../src

python setup.py

cd ../pyinstaller

python ${PREFIX}/pyinstaller.py CDJSVis.spec

cd dist

echo zip -r CDJSVis-${VERSION}.zip CDJSVis.app
zip -r CDJSVis-${VERSION}.zip CDJSVis.app

exit 0
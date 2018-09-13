#!/usr/bin/env bash

# Builds documentation and generates documentation diagrams from .uml
# files. Must be run from root project directory.

set -ex
rm -rf doc/build
sphinx-build -b html doc/source doc/build/html -W -n -v
python -m plantuml doc/source/diagrams/*.uml
mv doc/source/diagrams/*.png doc/source/images

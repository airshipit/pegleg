#!/usr/bin/env bash

# Builds documentation and generates documentation diagrams from .uml
# files. Must be run from root project directory.

set -ex

# Generate architectural images and move them into place.
python -m plantuml doc/source/diagrams/*.uml
mv doc/source/diagrams/*.png doc/source/images

# Build documentation.
rm -rf doc/build
sphinx-build -b html doc/source doc/build/html -W -n -v

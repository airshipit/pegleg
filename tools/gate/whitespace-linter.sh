#!/usr/bin/env bash

set -xe
RES=$(find . \
  -not -path "*/\.*" \
  -not -path "*/doc/build/*" \
  -not -path "*/doc/source/images/*" \
  -not -path "*/htmlcov/*" \
  -not -name "*.tgz" \
  -not -name "*.pyc" \
  -type f -exec egrep -l " +$" {} \;)

if [[ -n $RES ]]; then
  exit 1;
fi

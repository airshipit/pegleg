#!/usr/bin/env bash

set -x

RES=$(git grep -E -l -I " +$")

if [[ -n $RES ]]; then
  exit 1
fi

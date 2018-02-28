#!/usr/bin/env bash

set -e

realpath() {
    [[ $1 = /* ]] && echo "$1" || echo "$PWD/${1#./}"
}

SCRIPT_DIR=$(realpath "$(dirname "${0}")")
SOURCE_DIR=${SCRIPT_DIR}/pegleg
if [ -d "$PWD/global" ]; then
  WORKSPACE="$PWD"
else
  WORKSPACE=$(realpath "${SCRIPT_DIR}/..")
fi

IMAGE=${IMAGE:-quay.io/attcomdev/pegleg:latest}

docker run --rm -t \
    --net=none \
    -v "${WORKSPACE}:/workspace" \
    "${IMAGE}" \
    pegleg "${@}"

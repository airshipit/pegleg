#!/usr/bin/env bash

set -e

realpath() {
    [[ $1 = /* ]] && echo "$1" || echo "$PWD/${1#./}"
}

SCRIPT_DIR=$(realpath "$(dirname "${0}")")
SOURCE_DIR=${SCRIPT_DIR}/pegleg
if [ -z "${WORKSPACE}" ]; then
  WORKSPACE="/"
fi

IMAGE=${IMAGE:-quay.io/attcomdev/pegleg:latest}

echo
echo "== NOTE: Workspace $WORKSPACE  is available as /workspace in container context =="
echo

docker run --rm -t \
    --net=none \
    -v "${WORKSPACE}:/workspace" \
    "${IMAGE}" \
    pegleg "${@}"

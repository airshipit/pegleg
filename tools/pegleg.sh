#!/usr/bin/env bash

set -e

SCRIPT_DIR=$(realpath "$(dirname "${0}")")
SOURCE_DIR=${SCRIPT_DIR}/pegleg
if [ -d "$PWD/global" ]; then
  WORKSPACE="$PWD"
else
  WORKSPACE=$(realpath "${SCRIPT_DIR}/..")
fi

IMAGE_PEGLEG=${IMAGE_PEGLEG:-quay.io/attcomdev/pegleg:latest}

if [[ -z ${http_proxy} && -z ${https_proxy} ]]
then
    docker build -q --rm -t "${IMAGE_PEGLEG}" "${SOURCE_DIR}" > /dev/null
else
    docker build -q --rm -t "${IMAGE_PEGLEG}" --build-arg http_proxy=${http_proxy} --build-arg https_proxy=${https_proxy}  "${SOURCE_DIR}" > /dev/null
fi

docker run --rm -t \
    -v "${WORKSPACE}:/var/pegleg" \
    "${IMAGE_PEGLEG}" \
    pegleg "${@}"

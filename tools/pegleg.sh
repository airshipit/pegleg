#!/usr/bin/env bash

set -e

: ${WORKSPACE:=$(pwd)}
: ${IMAGE:=quay.io/airshipit/pegleg:latest}

echo
echo "== NOTE: Workspace $WORKSPACE is the execution directory in the container =="
echo

# Working directory inside container to execute commands from and mount from
# host OS
container_workspace_path='/workspace'

docker run --rm -t \
    --net=host \
    --workdir="$container_workspace_path" \
    -v "${WORKSPACE}:$container_workspace_path" \
    "${IMAGE}" \
    pegleg "${@}"

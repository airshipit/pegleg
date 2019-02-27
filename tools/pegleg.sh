#!/usr/bin/env bash

set -e

: ${WORKSPACE:=$(pwd)}
: ${IMAGE:=quay.io/airshipit/pegleg:latest-ubuntu_xenial}

: ${TERM_OPTS:=-it}

echo
echo "== NOTE: Workspace $WORKSPACE is the execution directory in the container =="
echo

# Working directory inside container to execute commands from and mount from
# host OS
container_workspace_path='/workspace'

docker run --rm $TERM_OPTS \
    --net=host \
    --workdir="$container_workspace_path" \
    -v "${HOME}/.ssh:${container_workspace_path}/.ssh" \
    -v "${WORKSPACE}:$container_workspace_path" \
    -e "PEGLEG_PASSPHRASE=$PEGLEG_PASSPHRASE" \
    -e "PEGLEG_SALT=$PEGLEG_SALT" \
    "${IMAGE}" \
    pegleg "${@}"

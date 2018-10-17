#!/usr/bin/env bash

set -e
posargs=$@
if [ ${#posargs} -ge 1 ]; then
    pytest -k  ${posargs}
else
    pytest
fi
set +e

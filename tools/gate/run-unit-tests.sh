#!/usr/bin/env bash

set -e
posargs=$@
# cross-platform way to derive the number of logical cores
readonly num_cores=$(python -c 'import multiprocessing as mp; print(mp.cpu_count())')
if [ ${#posargs} -ge 1 ]; then
    pytest -k ${posargs} -n $num_cores
else
    pytest -n $num_cores
fi
set +e

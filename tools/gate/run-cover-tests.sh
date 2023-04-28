#!/usr/bin/env bash

set -e
posargs=$@
# cross-platform way to derive the number of logical cores
readonly num_cores=$(python -c 'import multiprocessing as mp; print(mp.cpu_count())')
if [ ${#posargs} -ge 1 ]; then
    PATH=$PATH:~/.local/bin; pytest -vv -k ${posargs}  -n $num_cores --cov=pegleg --cov-report \
      html:cover --cov-report xml:cover/coverage.xml --cov-report term \
      --cov-fail-under 87 tests/
else
    pytest -n $num_cores
    PATH=$PATH:~/.local/bin; pytest -vv  -n $num_cores --cov=pegleg --cov-report \
      html:cover --cov-report xml:cover/coverage.xml --cov-report term \
      --cov-fail-under 87 tests/
fi
set +e

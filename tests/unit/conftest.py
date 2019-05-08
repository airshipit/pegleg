# Copyright 2018 AT&T Intellectual Property.  All other rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import atexit
import copy
import os
import shutil
import tempfile

import pytest

from pegleg import config
"""Fixtures that are applied to all unit tests."""


@pytest.fixture(autouse=True)
def restore_config():
    """Used for ensuring the original global context is reset in memory
    following each test execution.
    """
    original_global_context = copy.deepcopy(config.GLOBAL_CONTEXT)
    try:
        yield
    finally:
        config.GLOBAL_CONTEXT = original_global_context


# NOTE(felipemonteiro): This uses `atexit` rather than a `pytest.fixture`
# decorator because 1) this only needs to be run exactly once and 2) this
# works across multiple test executors via `pytest -n <num_cores>`
@atexit.register
def clean_temporary_git_repos():
    """Iterates through all temporarily created directories and deletes each
    one that was created for testing.

    """

    def temporary_git_repos():
        root_tempdir = tempfile.gettempdir()
        tempdirs = os.listdir(root_tempdir)
        for tempdir in tempdirs:
            path = os.path.join(root_tempdir, tempdir)
            if os.path.isdir(path) and os.access(path, os.R_OK):
                if any(p.startswith('airship') for p in os.listdir(path)):
                    yield path

    for tempdir in temporary_git_repos():
        shutil.rmtree(tempdir, ignore_errors=True)

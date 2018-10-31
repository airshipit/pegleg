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

import os

from pegleg import config
from pegleg.engine.util import files
from tests.unit.fixtures import create_tmp_deployment_files


class TestFileHelpers(object):
    def test_read_compatible_file(self, create_tmp_deployment_files):
        path = os.path.join(config.get_site_repo(), 'site', 'cicd', 'secrets',
                            'passphrases', 'cicd-passphrase.yaml')
        documents = files.read(path)
        assert 1 == len(documents)

    def test_read_incompatible_file(self, create_tmp_deployment_files):
        # NOTE(felipemonteiro): The Pegleg site-definition.yaml is a
        # Deckhand-formatted document currently but probably shouldn't be,
        # because it has no business being in Deckhand. As such, validate that
        # it is ignored.
        path = os.path.join(config.get_site_repo(), 'site', 'cicd',
                            'site-definition.yaml')
        documents = files.read(path)
        assert not documents, ("Documents returned should be empty for "
                               "site-definition.yaml")

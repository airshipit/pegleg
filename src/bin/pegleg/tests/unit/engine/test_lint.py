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

import mock

from pegleg.engine import lint
from pegleg.engine.util import files
from tests.unit.fixtures import create_tmp_deployment_files


def test_verify_deckhand_render_site_documents_separately(
        create_tmp_deployment_files):
    expected_documents = {
        'cicd': [
            'global-common', 'global-v1.0', 'cicd-type-common',
            'cicd-type-v1.0', 'cicd-chart', 'cicd-passphrase'
        ],
        'lab': [
            'global-common', 'global-v1.0', 'lab-type-common', 'lab-type-v1.0',
            'lab-chart', 'lab-passphrase'
        ],
    }

    with mock.patch(
            'pegleg.engine.util.deckhand.deckhand_render',
            autospec=True) as mock_render:
        mock_render.return_value = (None, [])

        result = lint._verify_deckhand_render()
        assert result == []

        sites = files.list_sites()

        # Verify that both expected site types are listed.
        assert sorted(sites) == ['cicd', 'lab']
        # Verify that Deckhand called render twice, once for each site.
        assert mock_render.call_count == 2

        mock_calls = list(mock_render.mock_calls)
        for mock_call in mock_calls:
            documents = mock_call[2]['documents']
            assert len(documents) == 7

            # Verify one site_definition.yaml per site.
            site_definitions = [x for x in documents if isinstance(x, dict)]
            assert len(site_definitions) == 1

            site_definition = site_definitions[0]
            site_type = site_definition['data']['site_type']

            assert site_definition['data']['revision'] == 'v1.0'
            assert site_type in expected_documents

            # Verify expected documents collected per site.
            other_documents = expected_documents[site_type]
            for other_document in other_documents:
                assert other_document in documents

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

        expected_sitenames = ['cicd', 'lab']
        sites = files.list_sites()

        # Verify that both expected site types are listed.
        assert sorted(sites) == expected_sitenames
        # Verify that Deckhand called render twice, once for each site.
        assert mock_render.call_count == 2

        expected_documents = []
        for sitename in expected_sitenames:
            documents = [{
                'data': 'global-common-password',
                'metadata': {
                    'layeringDefinition': {
                        'abstract': False,
                        'layer': 'global'
                    },
                    'name': 'global-common',
                    'schema': 'metadata/Document/v1',
                    'storagePolicy': 'cleartext'
                },
                'schema': 'deckhand/Passphrase/v1'
            }, {
                'data': 'global-v1.0-password',
                'metadata': {
                    'layeringDefinition': {
                        'abstract': False,
                        'layer': 'global'
                    },
                    'name': 'global-v1.0',
                    'schema': 'metadata/Document/v1',
                    'storagePolicy': 'cleartext'
                },
                'schema': 'deckhand/Passphrase/v1'
            }, {
                'data': '%s-type-common-password' % sitename,
                'metadata': {
                    'layeringDefinition': {
                        'abstract': False,
                        'layer': 'type'
                    },
                    'name': '%s-type-common' % sitename,
                    'schema': 'metadata/Document/v1',
                    'storagePolicy': 'cleartext'
                },
                'schema': 'deckhand/Passphrase/v1'
            }, {
                'data': '%s-type-v1.0-password' % sitename,
                'metadata': {
                    'layeringDefinition': {
                        'abstract': False,
                        'layer': 'type'
                    },
                    'name': '%s-type-v1.0' % sitename,
                    'schema': 'metadata/Document/v1',
                    'storagePolicy': 'cleartext'
                },
                'schema': 'deckhand/Passphrase/v1'
            }, {
                'data': '%s-chart-password' % sitename,
                'metadata': {
                    'layeringDefinition': {
                        'abstract': False,
                        'layer': 'site'
                    },
                    'name': '%s-chart' % sitename,
                    'schema': 'metadata/Document/v1',
                    'storagePolicy': 'cleartext'
                },
                'schema': 'deckhand/Passphrase/v1'
            }, {
                'data': '%s-passphrase-password' % sitename,
                'metadata': {
                    'layeringDefinition': {
                        'abstract': False,
                        'layer': 'site'
                    },
                    'name': '%s-passphrase' % sitename,
                    'schema': 'metadata/Document/v1',
                    'storagePolicy': 'cleartext'
                },
                'schema': 'deckhand/Passphrase/v1'
            }, {
                'data': {
                    'revision': 'v1.0',
                    'site_type': sitename
                },
                'metadata': {
                    'layeringDefinition': {
                        'abstract': False,
                        'layer': 'site'
                    },
                    'name': sitename,
                    'schema': 'metadata/Document/v1',
                    'storagePolicy': 'cleartext'
                },
                'schema': 'pegleg/SiteDefinition/v1'
            }]
            expected_documents.extend(documents)

        mock_calls = list(mock_render.mock_calls)
        actual_documents = []
        for mock_call in mock_calls:
            documents = mock_call[2]['documents']
            actual_documents.extend(documents)

        sort_func = lambda x: x['metadata']['name']
        assert sorted(
            expected_documents, key=sort_func) == sorted(
                actual_documents, key=sort_func)

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
import yaml

from pegleg import cli
from pegleg import config
from pegleg.engine import errorcodes
from pegleg.engine import lint
from pegleg.engine import site
from pegleg.engine.util import deckhand
from pegleg.engine.util import files
from tests.unit.fixtures import create_tmp_deployment_files


def _test_site_collect(expected_site, collection_path):
    site_definition = {
        'schema': 'pegleg/SiteDefinition/v1',
        'metadata': {
            'storagePolicy': 'cleartext',
            'schema': 'metadata/Document/v1',
            'layeringDefinition': {
                'abstract': False,
                'layer': 'site'
            },
            'name': expected_site
        },
        'data': {
            'site_type': expected_site,
            'revision': 'v1.0'
        }
    }
    expected_document_names = [
        'global-common',
        'global-v1.0',
        '%s-type-common' % expected_site,
        '%s-type-v1.0' % expected_site,
        site_definition['metadata']['name'],
        '%s-chart' % expected_site,
        '%s-passphrase' % expected_site,
    ]

    deployment_files = collection_path.join('deployment_files.yaml')
    assert deployment_files.isfile()

    with open(str(deployment_files), 'r') as f:
        lines = f.read()
        deployment_documents = list(yaml.safe_load_all(lines))

    assert sorted(expected_document_names) == sorted(
        [x['metadata']['name'] for x in deployment_documents])


def test_site_collect(tmpdir, create_tmp_deployment_files):
    collection_path = tmpdir.mkdir("cicd_path")
    site.collect("cicd", str(collection_path))
    _test_site_collect("cicd", collection_path)

    collection_path = tmpdir.mkdir("lab_path")
    site.collect("lab", str(collection_path))
    _test_site_collect("lab", collection_path)

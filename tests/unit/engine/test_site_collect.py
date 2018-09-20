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
import os
import shutil
import yaml

import click

from pegleg import cli
from pegleg import config
from pegleg.engine import errorcodes
from pegleg.engine import lint
from pegleg.engine import site
from pegleg.engine.util import deckhand
from pegleg.engine.util import files
from tests.unit.fixtures import create_tmp_deployment_files


def _site_definition(site_name):
    SITE_DEFINITION = {
        'schema': 'pegleg/SiteDefinition/v1',
        'metadata': {
            'storagePolicy': 'cleartext',
            'schema': 'metadata/Document/v1',
            'layeringDefinition': {
                'abstract': False,
                'layer': 'site'
            },
            'name': site_name
        },
        'data': {
            'site_type': site_name,
            'revision': 'v1.0'
        }
    }
    return SITE_DEFINITION


def _expected_document_names(site_name):
    EXPECTED_DOCUMENT_NAMES = [
        'global-common',
        'global-v1.0',
        '%s-type-common' % site_name,
        '%s-type-v1.0' % site_name,
        _site_definition(site_name)["metadata"]["name"],
        '%s-chart' % site_name,
        '%s-passphrase' % site_name,
    ]
    return EXPECTED_DOCUMENT_NAMES


def _test_site_collect_to_file(tmpdir, site_name, collection_path):
    try:
        collection_path = tmpdir.mkdir("cicd_path")
        collection_str_path = str(collection_path)
        site.collect(site_name, collection_str_path)

        deployment_files = collection_path.join('deployment_files.yaml')
        assert deployment_files.isfile()

        with open(str(deployment_files), 'r') as f:
            lines = f.read()
        deployment_documents = list(yaml.safe_load_all(lines))

        assert sorted(_expected_document_names(site_name)) == sorted(
            [x['metadata']['name'] for x in deployment_documents])
    finally:
        if os.path.exists(collection_str_path):
            shutil.rmtree(collection_str_path, ignore_errors=True)


def test_site_collect_to_file(tmpdir, create_tmp_deployment_files):
    _test_site_collect_to_file(tmpdir, "cicd", "cicd_path")
    _test_site_collect_to_file(tmpdir, "lab", "lab_path")


def _test_site_collect_to_stdout(site_name):
    # 2nd arg of None will force redirection to stdout.
    with mock.patch.object(click, 'echo') as mock_echo:
        site.collect(site_name, None)

    expected_names = _expected_document_names(site_name)
    all_lines = [x[1][0].strip() for x in mock_echo.mock_calls]

    assert all_lines, "Nothing written to stdout"
    for expected in expected_names:
        assert 'name: %s' % expected in all_lines


def test_site_collect_to_stdout(create_tmp_deployment_files):
    _test_site_collect_to_stdout("cicd")
    _test_site_collect_to_stdout("lab")


def test_read_and_format_yaml(tmpdir):
    # Validate the case where the YAML already begins with leading --- and ends
    # with trailing ... -- there should be no change.
    tempdir = tmpdir.mkdir(__name__)
    tempfile = tempdir.join("test-manifests-1.yaml")
    # Check that Linux-style newline is output instead when \r\n is provided.
    tempfile.write("---\r\nfoo:bar\r\n...\r\n")
    output = list(site._read_and_format_yaml(str(tempfile)))
    expected = ['---\n', 'foo:bar\n', '...\n']
    assert expected == output

    # Validate the case where the YAML is missing --- & ... and check that
    # they are added.
    tempfile = tempdir.join("test-manifests-2.yaml")
    tempfile.write("foo:bar\n")
    output = list(site._read_and_format_yaml(str(tempfile)))
    expected = ['---\n', 'foo:bar\n', '...\n']
    assert expected == output

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

import mock
import pytest
import yaml

from pegleg.engine import util
from pegleg.engine.util.shipyard_helper import ShipyardHelper
from pegleg.engine.util.shipyard_helper import ShipyardClient

# Dummy data to be used as collected documents
DATA = {
    'test-repo': [
        {
            'schema': 'pegleg/SiteDefinition/v1',
            'metadata': {
                'schema': 'metadata/Document/v1',
                'layeringDefinition': {
                    'abstract': False,
                    'layer': 'site'
                },
                'name': 'site-name',
                'storagePolicy': 'cleartext'
            },
            'data': {
                'site_type': 'foundry'
            }
        }
    ]
}

MULTI_REPO_DATA = {
    'repo1': [
        {
            'schema': 'pegleg/SiteDefinition/v1',
            'metadata': {
                'schema': 'metadata/Document/v1',
                'layeringDefinition': {
                    'abstract': False,
                    'layer': 'site'
                },
                'name': 'site-name',
                'storagePolicy': 'cleartext'
            },
            'data': {
                'site_type': 'foundry'
            }
        }
    ],
    'repo2': [
        {
            'schema': 'pegleg/SiteDefinition/v1',
            'metadata': {
                'schema': 'metadata/Document/v1',
                'layeringDefinition': {
                    'abstract': False,
                    'layer': 'site'
                },
                'name': 'site-name',
                'storagePolicy': 'cleartext'
            },
            'data': {
                'site_type': 'foundry'
            }
        }
    ]
}


@pytest.fixture(autouse=True)
def set_env_vars(monkeypatch):
    monkeypatch.setenv("PEGLEG_PASSPHRASE", "1234567890123456789012345678")
    monkeypatch.setenv("PEGLEG_SALT", "1234567890")


class context():
    obj = {}


class FakeResponse():
    code = 404


def _get_context():
    ctx = context()
    ctx.obj = {}
    auth_vars = {
        'project_domain_name': 'projDomainTest',
        'user_domain_name': 'userDomainTest',
        'project_name': 'projectTest',
        'username': 'usernameTest',
        'password': 'passwordTest',
        'auth_url': 'urlTest'
    }
    ctx.obj['API_PARAMETERS'] = {'auth_vars': auth_vars}
    ctx.obj['context_marker'] = '88888888-4444-4444-4444-121212121212'
    ctx.obj['site_name'] = 'test-site'
    ctx.obj['collection'] = 'test-site'
    return ctx


def _get_bad_context():
    ctx = context()
    ctx.obj = {}
    auth_vars = {
        'project_domain_name': 'projDomainTest',
        'user_domain_name': 'userDomainTest',
        'project_name': 'projectTest',
        'username': 'usernameTest',
        'password': 'passwordTest',
        'auth_url': None
    }
    ctx.obj['API_PARAMETERS'] = {'auth_vars': auth_vars}
    ctx.obj['context_marker'] = '88888888-4444-4444-4444-121212121212'
    ctx.obj['site_name'] = 'test-site'
    ctx.obj['collection'] = None
    return ctx


def _get_data_as_collection(data):
    collection = []
    for repo, documents in data.items():
        for document in documents:
            collection.append(document)
    return yaml.dump_all(collection, Dumper=yaml.SafeDumper)


def test_shipyard_helper_init_():
    """ Tests ShipyardHelper init method """
    # Scenario:
    #
    # 1) Get a dummy context Object
    # 2) Check that site name is as expected
    # 3) Check api client is instance of ShipyardClient

    context = _get_context()
    shipyard_helper = ShipyardHelper(context)

    assert shipyard_helper.site_name == context.obj['site_name']
    assert isinstance(shipyard_helper.api_client, ShipyardClient)


@mock.patch(
    'pegleg.engine.util.files.collect_files_by_repo',
    autospec=True,
    return_value=MULTI_REPO_DATA)
@mock.patch.object(
    ShipyardHelper,
    'formatted_response_handler',
    autospec=True,
    return_value=None)
@mock.patch.dict(
    os.environ, {
        'PEGLEG_PASSPHRASE': 'ytrr89erARAiPE34692iwUMvWqqBvC',
        'PEGLEG_SALT': 'MySecretSalt1234567890]['
    })
def test_upload_documents(*args):
    """ Tests upload document """
    # Scenario:
    #
    # 1) Get a dummy context Object
    # 2) Mock external calls
    # 3) Check documents uploaded to Shipyard with correct parameters

    context = _get_context()
    with mock.patch('pegleg.engine.util.shipyard_helper.ShipyardClient',
                    autospec=True) as mock_shipyard:
        mock_api_client = mock_shipyard.return_value
        mock_api_client.post_configdocs.return_value = 'Success'
        result = ShipyardHelper(context, 'replace').upload_documents()

        # Validate Shipyard call to post configdocs was invoked with correct
        # collection name and buffer mode.
        expected_data = _get_data_as_collection(MULTI_REPO_DATA)
        mock_api_client.post_configdocs.assert_called_with(
            collection_id='test-site',
            buffer_mode='replace',
            document_data=expected_data)
        mock_api_client.post_configdocs.assert_called_once()


@mock.patch(
    'pegleg.engine.util.files.collect_files_by_repo',
    autospec=True,
    return_value=DATA)
@mock.patch.object(
    ShipyardHelper,
    'formatted_response_handler',
    autospec=True,
    return_value=None)
@mock.patch.dict(
    os.environ, {
        'PEGLEG_PASSPHRASE': 'ytrr89erARAiPE34692iwUMvWqqBvC',
        'PEGLEG_SALT': 'MySecretSalt1234567890]['
    })
def test_upload_documents_fail(*args):
    """ Tests Document upload error """
    # Scenario:
    #
    # 1) Get a bad context object with empty auth_url
    # 2) Mock external calls
    # 3) Check DocumentUploadError is raised

    context = _get_context()
    shipyard_helper = ShipyardHelper(context)

    with mock.patch('pegleg.engine.util.shipyard_helper.ShipyardClient',
                    autospec=True) as mock_shipyard:
        mock_api_client = mock_shipyard.return_value
        mock_api_client.post_configdocs.return_value = FakeResponse()
        with pytest.raises(util.shipyard_helper.DocumentUploadError):
            ShipyardHelper(context).upload_documents()


@mock.patch(
    'pegleg.engine.util.files.collect_files_by_repo',
    autospec=True,
    return_value=DATA)
@mock.patch.object(
    ShipyardHelper,
    'formatted_response_handler',
    autospec=True,
    return_value=None)
def test_fail_auth(*args):
    """ Tests Auth Failure """
    # Scenario:
    #
    # 1) Get a bad context object with empty auth_url
    # 2) Check AuthValuesError is raised

    context = _get_bad_context()
    shipyard_helper = ShipyardHelper(context)

    with pytest.raises(util.shipyard_helper.AuthValuesError):
        ShipyardHelper(context).validate_auth_vars()


@mock.patch.object(
    ShipyardHelper,
    'formatted_response_handler',
    autospec=True,
    return_value=None)
def test_commit_documents(*args):
    """Tests commit document """
    # Scenario:
    #
    # 1) Get a dummy context Object
    # 2) Mock external calls
    # 3) Check commit documents was called

    context = _get_context()
    shipyard_helper = ShipyardHelper(context)

    with mock.patch('pegleg.engine.util.shipyard_helper.ShipyardClient',
                    autospec=True) as mock_shipyard:
        mock_api_client = mock_shipyard.return_value
        mock_api_client.commit_configdocs.return_value = 'Success'
        result = ShipyardHelper(context).commit_documents()

        mock_api_client.commit_configdocs.assert_called_once()

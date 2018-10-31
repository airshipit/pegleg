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
from pegleg.engine.errorcodes import DECKHAND_DUPLICATE_SCHEMA
from pegleg.engine.errorcodes import DECKHAND_RENDER_EXCEPTION
from pegleg.engine.util import deckhand
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


@mock.patch('pegleg.engine.util.deckhand.deckhand_render')
def test_verify_deckhand_render_error_handling(mock_render):
    """
    Verifying deckhand render error handling.

    Parameters:
        mock_render: Mock render object.
    """
    exp_dict = {
        'exp1':
        DECKHAND_DUPLICATE_SCHEMA + ": Duplicate schema specified.\n",
        'exp2':
        DECKHAND_RENDER_EXCEPTION +
        ": An unknown Deckhand exception occurred while trying to render documents\n",
        'exp3':
        "Generic Error\n"
    }
    # No exception raised
    mock_render.return_value = _return_deckhand_render_errors()
    errors = deckhand.deckhand_render()
    assert errors == []
    # check errors object type
    mock_render.return_value = _return_deckhand_render_errors(1)
    errors = deckhand.deckhand_render()
    assert isinstance(errors, list)
    # check single exception handling
    assert _deckhand_render_exception_msg(errors) == exp_dict['exp1']
    # check multiple exception with tuple type
    mock_render.return_value = _return_deckhand_render_errors(2)
    errors = deckhand.deckhand_render()
    assert _deckhand_render_exception_msg(
        errors) == exp_dict['exp1'] + exp_dict['exp2']
    # check multiple exception with mixed type
    mock_render.return_value = _return_deckhand_render_errors(3)
    errors = deckhand.deckhand_render()
    assert _deckhand_render_exception_msg(
        errors) == exp_dict['exp1'] + exp_dict['exp2'] + exp_dict['exp3']


def _deckhand_render_exception_msg(errors):
    """
    Helper function to create deckhand render exception msg.

    Parameters:
        errors: List of errors provided by deckhand render.
    Returns:
        string: formulated error message.
    """
    err_msg = ''
    for err in errors:
        if isinstance(err, tuple) and len(err) > 1:
            err_msg += ': '.join(err) + '\n'
        else:
            err_msg += str(err) + '\n'
    return err_msg


def _return_deckhand_render_errors(error_count=0):
    """
    Helper function to mock deckhand render errors.

    Parameters:
        error_count: Number of mock errors to return.
    Returns:
        List: List of mock errors as per error_count.
    """
    errors = []
    if error_count >= 1:
        errors.append((DECKHAND_DUPLICATE_SCHEMA,
                       'Duplicate schema specified.'))
    if error_count >= 2:
        errors.append((DECKHAND_RENDER_EXCEPTION,
                       'An unknown Deckhand exception occurred while '
                       'trying to render documents'))
    if error_count >= 3:
        errors.append(('Generic Error'))
    return errors

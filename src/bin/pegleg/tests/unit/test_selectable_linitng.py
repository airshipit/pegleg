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
import click
import mock
import pytest

from pegleg import config
from pegleg.engine import lint


@mock.patch.object(lint, '_verify_deckhand_render', return_value=[])
@mock.patch.object(lint, '_verify_no_unexpected_files', return_value=[])
def test_lint_excludes_P001(*args):
    exclude_lint = ['P001']
    config.set_primary_repo('../pegleg/site_yamls/')

    msg_1 = 'is a secret, but has unexpected storagePolicy: "cleartext"'
    msg_2 = 'test msg'
    msgs = [msg_1, msg_2]

    with mock.patch.object(lint, '_verify_file_contents', return_value=msgs) as mock_methed:
        with pytest.raises(click.ClickException) as expected_exc:
            results = lint.full(False, exclude_lint, [])
            e = str(expected_exc)
            assert msg_1 in expected_exc
            assert msg_2 in expected_exc


@mock.patch.object(lint, '_verify_no_unexpected_files', return_value=[])
def test_lint_excludes_P002(*args):
    exclude_lint = ['P002']
    config.set_primary_repo('../pegleg/site_yamls/')
    with mock.patch.object(lint, '_verify_deckhand_render') as mock_method:
        lint.full(False, exclude_lint, [])
    mock_method.assert_not_called()


@mock.patch.object(lint, '_verify_deckhand_render', return_value=[])
def test_lint_excludes_P003(*args):
    exclude_lint = ['P003']
    with mock.patch.object(lint, '_verify_no_unexpected_files') as mock_method:
        lint.full(False, exclude_lint, [])
    mock_method.assert_not_called()


@mock.patch.object(lint, '_verify_deckhand_render', return_value=[])
@mock.patch.object(lint, '_verify_no_unexpected_files', return_value=[])
def test_lint_warns_P001(*args):
    warn_lint = ['P001']
    config.set_primary_repo('../pegleg/site_yamls/')

    msg_1 = 'is a secret, but has unexpected storagePolicy: "cleartext"'
    msg_2 = 'test msg'
    msgs = [msg_1, msg_2]

    with mock.patch.object(lint, '_verify_file_contents', return_value=msgs) as mock_methed:
        with pytest.raises(click.ClickException) as expected_exc:
            lint.full(False, [], warn_lint)
            e = str(expected_exc)
            assert msg_1 not in expected_exc
            assert msg_2 in expected_exc


@mock.patch.object(lint, '_verify_no_unexpected_files', return_value=[])
def test_lint_warns_P002(*args):
    warn_lint = ['P002']
    config.set_primary_repo('../pegleg/site_yamls/')

    with mock.patch.object(lint, '_verify_deckhand_render') as mock_method:
        lint.full(False, [], warn_lint)
    mock_method.assert_called()


@mock.patch.object(lint, '_verify_deckhand_render', return_value=[])
def test_lint_warns_P003(*args):
    warn_lint = ['P003']
    config.set_primary_repo('../pegleg/site_yamls/')

    with mock.patch.object(lint, '_verify_no_unexpected_files') as mock_method:
        lint.full(False, [], warn_lint)
    mock_method.assert_called()

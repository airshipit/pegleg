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
from tests.unit.fixtures import create_tmp_deployment_files

_SKIP_P003_REASON = """Currently broken with revisioned repositories
directory layout changes. The old pseudo-revision folders like 'v4.0' are
no longer relevant and so the lint logic for this rule needs to be updated.
For more information, see: https://storyboard.openstack.org/#!/story/2003762
"""


class TestSelectableLinting(object):
    @mock.patch.object(lint, '_verify_deckhand_render', return_value=[])
    @mock.patch.object(lint, '_verify_no_unexpected_files', return_value=[])
    def test_lint_excludes_P001(*args):
        exclude_lint = ['P001']
        config.set_site_repo('../pegleg/site_yamls/')

        code_1 = 'X001'
        msg_1 = 'is a secret, but has unexpected storagePolicy: "cleartext"'
        code_2 = 'X002'
        msg_2 = 'test msg'
        msgs = [(code_1, msg_1), (code_2, msg_2)]

        with mock.patch.object(
                lint, '_verify_file_contents',
                return_value=msgs) as mock_methed:
            with pytest.raises(click.ClickException) as expected_exc:
                results = lint.full(False, exclude_lint, [])
                assert msg_1 in expected_exc
                assert msg_2 in expected_exc

    @pytest.mark.skip(reason=_SKIP_P003_REASON)
    @mock.patch.object(lint, '_verify_deckhand_render', return_value=[])
    def test_lint_excludes_P003(*args):
        exclude_lint = ['P003']
        with mock.patch.object(
                lint,
                '_verify_no_unexpected_files',
                return_value=[('P003', 'test message')]) as mock_method:
            lint.full(False, exclude_lint, [])
        mock_method.assert_called()

    @mock.patch.object(lint, '_verify_deckhand_render', return_value=[])
    @mock.patch.object(lint, '_verify_no_unexpected_files', return_value=[])
    def test_lint_warns_P001(*args):
        warn_lint = ['P001']
        config.set_site_repo('../pegleg/site_yamls/')

        code_1 = 'X001'
        msg_1 = 'is a secret, but has unexpected storagePolicy: "cleartext"'
        code_2 = 'X002'
        msg_2 = 'test msg'
        msgs = [(code_1, msg_1), (code_2, msg_2)]

        with mock.patch.object(
                lint, '_verify_file_contents',
                return_value=msgs) as mock_methed:
            with pytest.raises(click.ClickException) as expected_exc:
                lint.full(False, [], warn_lint)
                assert msg_1 not in expected_exc
                assert msg_2 in expected_exc

    @pytest.mark.skip(reason=_SKIP_P003_REASON)
    @mock.patch.object(lint, '_verify_deckhand_render', return_value=[])
    def test_lint_warns_P003(*args):
        warn_lint = ['P003']
        config.set_site_repo('../pegleg/site_yamls/')

        with mock.patch.object(lint,
                               '_verify_no_unexpected_files') as mock_method:
            lint.full(False, [], warn_lint)
        mock_method.assert_called()


class TestSelectableLintingHelperFunctions(object):
    """The fixture ``create_tmp_deployment_files`` produces many linting errors
    by default.

    """

    def test_verify_file_contents(self, create_tmp_deployment_files):
        """Validate that linting by a specific site ("cicd") produces a subset
        of all the linting errors produced for all sites.

        """

        all_lint_errors = lint._verify_file_contents()
        assert all_lint_errors

        cicd_lint_errors = lint._verify_file_contents(sitename="cicd")
        assert cicd_lint_errors

        assert len(cicd_lint_errors) < len(all_lint_errors)

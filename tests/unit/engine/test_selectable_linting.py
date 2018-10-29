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

import click
import mock
import pytest

from deckhand.engine import layering
from deckhand import errors as dh_errors

from pegleg import config
from pegleg.engine import errorcodes
from pegleg.engine import lint
from tests.unit.fixtures import create_tmp_deployment_files

_SKIP_P003_REASON = """Currently broken with revisioned repositories
directory layout changes. The old pseudo-revision folders like 'v4.0' are
no longer relevant and so the lint logic for this rule needs to be updated.
For more information, see: https://storyboard.openstack.org/#!/story/2003762
"""


class TestSelectableLinting(object):
    def setup(self):
        self.site_yaml_path = os.path.join(os.getcwd(), 'site_yamls')

    def _exclude_all(self, except_code):
        """Helper to generate list of all error codes to exclude except for
        ``except_code`` in order to isolate tests that focus on validating
        ``warn_lint``: Just check that the expected code issues a warning and
        effectively ignore all other errors.
        """
        return [code for code in errorcodes.ALL_CODES if code != except_code]

    @mock.patch.object(lint, '_verify_deckhand_render', return_value=[])
    @mock.patch.object(lint, '_verify_no_unexpected_files', return_value=[])
    def test_lint_excludes_P001(self, *args):
        """Test exclude flag for P001 - Document has storagePolicy cleartext
        (expected is encrypted) yet its schema is a mandatory encrypted type.
        """
        exclude_lint = ['P001']
        config.set_site_repo(self.site_yaml_path)

        code_1 = 'X001'
        msg_1 = 'is a secret, but has unexpected storagePolicy: "cleartext"'
        code_2 = 'X002'
        msg_2 = 'test msg'
        msgs = [(code_1, msg_1), (code_2, msg_2)]

        with mock.patch.object(
                lint, '_verify_file_contents',
                return_value=msgs) as mock_methed:
            with pytest.raises(click.ClickException) as expected_exc:
                lint.full(False, exclude_lint, [])
                assert msg_1 in expected_exc
                assert msg_2 in expected_exc

    @pytest.mark.skip(reason=_SKIP_P003_REASON)
    @mock.patch.object(lint, '_verify_deckhand_render', return_value=[])
    def test_lint_excludes_P003(self, *args):
        """Test exclude flag for P003 - All repos contain expected
        directories.
        """
        exclude_lint = ['P003']
        with mock.patch.object(
                lint,
                '_verify_no_unexpected_files',
                return_value=[('P003', 'test message')]) as mock_method:
            result = lint.full(False, exclude_lint, [])
        mock_method.assert_called()
        assert not result  # Exclude doesn't return anything.

    @mock.patch.object(lint, '_verify_deckhand_render', return_value=[])
    @mock.patch.object(lint, '_verify_no_unexpected_files', return_value=[])
    def test_lint_warns_P001(self, *args):
        """Test lint flag for P001 - Document has storagePolicy cleartext
        (expected is encrypted) yet its schema is a mandatory encrypted type.
        """
        exclude_lint = self._exclude_all(except_code='P001')
        warn_lint = ['P001']
        config.set_site_repo(self.site_yaml_path)

        code_1 = 'X001'
        msg_1 = 'is a secret, but has unexpected storagePolicy: "cleartext"'
        code_2 = 'X002'
        msg_2 = 'test msg'
        msgs = [(code_1, msg_1), (code_2, msg_2)]

        with mock.patch.object(
                lint, '_verify_file_contents',
                return_value=msgs) as mock_methed:
            with pytest.raises(click.ClickException) as expected_exc:
                lint.full(
                    False, exclude_lint=exclude_lint, warn_lint=warn_lint)
                assert msg_1 not in expected_exc
                assert msg_2 in expected_exc

    @pytest.mark.skip(reason=_SKIP_P003_REASON)
    @mock.patch.object(lint, '_verify_deckhand_render', return_value=[])
    def test_lint_warns_P003(self, *args):
        """Test warn flag for P003 - All repos contain expected directories."""
        exclude_lint = self._exclude_all(except_code='P003')
        warn_lint = ['P003']
        config.set_site_repo(self.site_yaml_path)

        with mock.patch.object(lint,
                               '_verify_no_unexpected_files') as mock_method:
            result = lint.full(
                False, exclude_lint=exclude_lint, warn_lint=warn_lint)
        mock_method.assert_called()
        assert len(result) == 1
        assert result[0].startswith(warn_lint[0])

    @mock.patch('pegleg.engine.util.deckhand.layering', autospec=True)
    def test_lint_warns_P004(self, mock_layering):
        """Test warn flag for P004 - Duplicate Deckhand DataSchema document
        detected.
        """
        # Stub out Deckhand render logic.
        mock_layering.DocumentLayering.return_value.render.return_value = []

        exclude_lint = self._exclude_all(except_code='P004')
        warn_lint = ['P004']
        config.set_site_repo(self.site_yaml_path)

        documents = {
            mock.sentinel.site: [{
                # Create 2 duplicate DataSchema documents.
                "schema": "deckhand/DataSchema/v1",
                "metadata": {
                    "name": mock.sentinel.document_name
                },
                "data": {}
            }] * 2
        }

        with mock.patch(
                'pegleg.engine.util.definition.documents_for_each_site',
                autospec=True,
                return_value=documents):
            result = lint.full(
                False, exclude_lint=exclude_lint, warn_lint=warn_lint)
        assert len(result) == 1
        assert result[0].startswith(warn_lint[0])

    @mock.patch('pegleg.engine.util.deckhand.layering', autospec=True)
    def test_lint_warns_P005(self, mock_layering):
        """Test warn flag for P005 - Deckhand rendering exception."""
        # Make Deckhand render expected exception to trigger error code.
        mock_layering.DocumentLayering.return_value.render.side_effect = (
            dh_errors.DeckhandException)

        exclude_lint = self._exclude_all(except_code='P005')
        warn_lint = ['P005']
        config.set_site_repo(self.site_yaml_path)

        documents = {
            mock.sentinel.site: [{
                "schema": "deckhand/DataSchema/v1",
                "metadata": {
                    "name": mock.sentinel.document_name
                },
                "data": {}
            }]
        }

        with mock.patch(
                'pegleg.engine.util.definition.documents_for_each_site',
                autospec=True,
                return_value=documents):
            result = lint.full(
                False, exclude_lint=exclude_lint, warn_lint=warn_lint)
        assert len(result) == 1
        assert result[0].startswith(warn_lint[0])

    def test_lint_warns_P006(self, tmpdir):
        """Test warn flag for P006 - YAML file missing document header."""

        exclude_lint = self._exclude_all(except_code='P006')
        warn_lint = ['P006']
        config.set_site_repo(self.site_yaml_path)

        p = tmpdir.mkdir(self.__class__.__name__).join("test.yaml")
        p.write("foo: bar")

        with mock.patch(
                'pegleg.engine.util.files.all',
                autospec=True,
                return_value=[p.strpath]):
            result = lint.full(
                False, exclude_lint=exclude_lint, warn_lint=warn_lint)
        assert len(result) == 1
        assert result[0].startswith(warn_lint[0])

    def test_lint_warns_P007(self, tmpdir):
        """Test warn flag for P007 - YAML file is not valid YAML."""

        exclude_lint = self._exclude_all(except_code='P007')
        warn_lint = ['P007']
        config.set_site_repo(self.site_yaml_path)

        p = tmpdir.mkdir(self.__class__.__name__).join("test.yaml")
        # Invalid YAML - will trigger error.
        p.write("---\nfoo: bar: baz")

        with mock.patch(
                'pegleg.engine.util.files.all',
                autospec=True,
                return_value=[p.strpath]):
            result = lint.full(
                False, exclude_lint=exclude_lint, warn_lint=warn_lint)
        assert len(result) == 1
        assert result[0].startswith(warn_lint[0])

    # TODO(felipemonteiro): Add tests for P008, P009.


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

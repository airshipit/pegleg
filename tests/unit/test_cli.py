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
import requests
import shutil
import tempfile

from click.testing import CliRunner
import mock
import pytest

from pegleg import cli
from pegleg.engine import errorcodes
from pegleg.engine.util import git


def is_connected():
    """Verifies whether network connectivity is up.

    :returns: True if connected else False.
    """
    try:
        r = requests.get("http://www.github.com/", proxies={})
        return r.ok
    except requests.exceptions.RequestException:
        return False


@pytest.mark.skipif(
    not is_connected(), reason='git clone requires network connectivity.')
class BaseCLIActionTest(object):
    """Tests end-to-end flows for all Pegleg CLI actions, with minimal mocking.

    General pattern should be to include exactly one test that uses a remote
    repo URL and as many other tests that are required that use a local repo
    path for runtime optimization.

    """

    # TODO(felipemonteiro): Need tests that validate repository overrides. Also
    # need to write tests that use a site-defintion.yaml with repositories key.

    @classmethod
    def setup_class(cls):
        cls.runner = CliRunner()

        # Pin so we know that airship-seaworthy is a valid site.
        cls.site_name = "airship-seaworthy"
        cls.repo_rev = '6b183e148b9bb7ba6f75c98dd13451088255c60b'
        cls.repo_name = "airship-treasuremap"
        repo_url = "https://github.com/openstack/%s.git" % cls.repo_name
        cls.treasuremap_path = git.git_handler(repo_url, ref=cls.repo_rev)

    @classmethod
    def teardown_class(cls):
        # Cleanup temporary Git repos.
        root_tempdir = tempfile.gettempdir()
        for tempdir in os.listdir(root_tempdir):
            path = os.path.join(root_tempdir, tempdir)
            if git.is_repository(path):
                shutil.rmtree(path, ignore_errors=True)


class TestSiteCliActions(BaseCLIActionTest):
    """Tests site-level CLI actions."""

    ### Collect tests ###

    def test_collect_using_remote_repo_url(self):
        """Validates collect action using a remote URL."""
        # Scenario:
        #
        # 1) Create temporary save location
        # 2) Collect into save location (should clone repo automatically)
        # 3) Check that expected file name is there

        save_location = tempfile.mkdtemp()
        repo_url = 'https://github.com/openstack/%s@%s' % (self.repo_name,
                                                           self.repo_rev)
        result = self.runner.invoke(
            cli.site,
            ['-r', repo_url, 'collect', self.site_name, '-s', save_location])

        collected_files = os.listdir(save_location)

        assert result.exit_code == 0
        assert len(collected_files) == 1
        # Validates that site manifests collected from cloned repositories
        # are written out to sensibly named files like airship-treasuremap.yaml
        assert collected_files[0] == ("%s.yaml" % self.repo_name)

    def test_collect_using_local_path(self):
        """Validates collect action using a path to a local repo."""
        # Scenario:
        #
        # 1) Create temporary save location
        # 2) Collect into save location (should skip clone repo)
        # 3) Check that expected file name is there

        save_location = tempfile.mkdtemp()
        repo_path = self.treasuremap_path

        result = self.runner.invoke(
            cli.site,
            ['-r', repo_path, 'collect', self.site_name, '-s', save_location])

        collected_files = os.listdir(save_location)

        assert result.exit_code == 0
        assert len(collected_files) == 1
        # Validates that site manifests collected from cloned repositories
        # are written out to sensibly named files like airship-treasuremap.yaml
        assert collected_files[0] == ("%s.yaml" % self.repo_name)

    ### Lint tests ###

    def test_lint_site_using_remote_repo_url_with_exclude(self):
        """Validates site lint action using remote repo URL."""
        # Scenario:
        #
        # 1) Mock out Deckhand render (so we can ignore P005 issues)
        # 2) Lint site with exclude flags (should clone repo automatically)

        repo_url = 'https://github.com/openstack/%s@%s' % (self.repo_name,
                                                           self.repo_rev)

        lint_command = ['-r', repo_url, 'lint', self.site_name]
        exclude_lint_command = [
            '-x', errorcodes.SCHEMA_STORAGE_POLICY_MISMATCH_FLAG, '-x',
            errorcodes.SECRET_NOT_ENCRYPTED_POLICY
        ]

        with mock.patch('pegleg.engine.site.util.deckhand') as mock_deckhand:
            mock_deckhand.deckhand_render.return_value = ([], [])
            result = self.runner.invoke(cli.site,
                                        lint_command + exclude_lint_command)

        assert result.exit_code == 0
        # A successful result (while setting lint checks to exclude) should
        # output nothing.
        assert not result.output

    def test_lint_site_using_local_path_with_exclude(self):
        """Validates site lint action using local repo path."""
        # Scenario:
        #
        # 1) Mock out Deckhand render (so we can ignore P005 issues)
        # 2) Lint site with exclude flags (should skip clone repo)

        repo_path = self.treasuremap_path
        lint_command = ['-r', repo_path, 'lint', self.site_name]
        exclude_lint_command = [
            '-x', errorcodes.SCHEMA_STORAGE_POLICY_MISMATCH_FLAG, '-x',
            errorcodes.SECRET_NOT_ENCRYPTED_POLICY
        ]

        with mock.patch('pegleg.engine.site.util.deckhand') as mock_deckhand:
            mock_deckhand.deckhand_render.return_value = ([], [])
            result = self.runner.invoke(cli.site,
                                        lint_command + exclude_lint_command)

        assert result.exit_code == 0
        # A successful result (while setting lint checks to exclude) should
        # output nothing.
        assert not result.output

    def test_lint_site_using_local_path_with_warn(self):
        """Validates site lint action using local repo path."""
        # Scenario:
        #
        # 1) Mock out Deckhand render (so we can ignore P005 issues)
        # 2) Lint site with warn flags (should skip clone repo)

        repo_path = self.treasuremap_path
        lint_command = ['-r', repo_path, 'lint', self.site_name]
        warn_lint_command = [
            '-w', errorcodes.SCHEMA_STORAGE_POLICY_MISMATCH_FLAG, '-w',
            errorcodes.SECRET_NOT_ENCRYPTED_POLICY
        ]

        with mock.patch('pegleg.engine.site.util.deckhand') as mock_deckhand:
            mock_deckhand.deckhand_render.return_value = ([], [])
            result = self.runner.invoke(cli.site,
                                        lint_command + warn_lint_command)

        assert result.exit_code == 0
        # A successful result (while setting lint checks to warns) should
        # output warnings.
        assert result.output

    ### List tests ###

    def test_list_sites_using_remote_repo_url(self):
        """Validates list action using remote repo URL."""
        # Scenario:
        #
        # 1) List sites (should clone repo automatically)

        repo_url = 'https://github.com/openstack/%s@%s' % (self.repo_name,
                                                           self.repo_rev)

        # NOTE(felipemonteiro): Pegleg currently doesn't dump a table to stdout
        # for this CLI call so mock out the csv DictWriter to determine output.
        with mock.patch('pegleg.engine.site.csv.DictWriter') as mock_writer:
            result = self.runner.invoke(cli.site, ['-r', repo_url, 'list'])

        assert result.exit_code == 0
        m_writer = mock_writer.return_value
        m_writer.writerow.assert_called_once_with({
            'site_type': 'foundry',
            'site_name': self.site_name
        })

    def test_list_sites_using_local_path(self):
        """Validates list action using local repo path."""
        # Scenario:
        #
        # 1) List sites (should skip clone repo)

        repo_path = self.treasuremap_path

        # NOTE(felipemonteiro): Pegleg currently doesn't dump a table to stdout
        # for this CLI call so mock out the csv DictWriter to determine output.
        with mock.patch('pegleg.engine.site.csv.DictWriter') as mock_writer:
            result = self.runner.invoke(cli.site, ['-r', repo_path, 'list'])

        assert result.exit_code == 0
        m_writer = mock_writer.return_value
        m_writer.writerow.assert_called_once_with({
            'site_type': 'foundry',
            'site_name': self.site_name
        })

    ### Show tests ###

    def test_show_site_using_remote_repo_url(self):
        """Validates show action using remote repo URL."""
        # Scenario:
        #
        # 1) Show site (should clone repo automatically)

        repo_url = 'https://github.com/openstack/%s@%s' % (self.repo_name,
                                                           self.repo_rev)

        with mock.patch('pegleg.engine.site.json') as mock_json:
            result = self.runner.invoke(
                cli.site, ['-r', repo_url, 'show', self.site_name])

        assert result.exit_code == 0
        assert mock_json.dump.called
        mock_calls = mock_json.dump.mock_calls
        assert mock_calls[0][1][0] == {
            'files': mock.ANY,
            'site_type': 'foundry',
            'site_name': self.site_name
        }

    def test_show_site_using_local_path(self):
        """Validates show action using local repo path."""
        # Scenario:
        #
        # 1) Show site (should skip clone repo)

        repo_path = self.treasuremap_path
        with mock.patch('pegleg.engine.site.json') as mock_json:
            result = self.runner.invoke(
                cli.site, ['-r', repo_path, 'show', self.site_name])

        assert result.exit_code == 0
        assert mock_json.dump.called
        mock_calls = mock_json.dump.mock_calls
        assert mock_calls[0][1][0] == {
            'files': mock.ANY,
            'site_type': 'foundry',
            'site_name': self.site_name
        }

    ### Render tests ###

    def test_render_site_using_remote_repo_url(self):
        """Validates render action using remote repo URL."""
        # Scenario:
        #
        # 1) Mock out Deckhand render (so we can ignore P005 issues)
        # 2) Render site (should clone repo automatically)

        repo_url = 'https://github.com/openstack/%s@%s' % (self.repo_name,
                                                           self.repo_rev)

        render_command = ['-r', repo_url, 'render', self.site_name]

        with mock.patch('pegleg.engine.site.yaml') as mock_yaml:
            with mock.patch(
                    'pegleg.engine.site.util.deckhand') as mock_deckhand:
                mock_deckhand.deckhand_render.return_value = ([], [])
                result = self.runner.invoke(cli.site, render_command)

        assert result.exit_code == 0
        mock_yaml.dump_all.assert_called_once()

    def test_render_site_using_local_path(self):
        """Validates render action using local repo path."""
        # Scenario:
        #
        # 1) Mock out Deckhand render (so we can ignore P005 issues)
        # 2) Render site (should skip clone repo)

        repo_path = self.treasuremap_path
        render_command = ['-r', repo_path, 'render', self.site_name]

        with mock.patch('pegleg.engine.site.yaml') as mock_yaml:
            with mock.patch(
                    'pegleg.engine.site.util.deckhand') as mock_deckhand:
                mock_deckhand.deckhand_render.return_value = ([], [])
                result = self.runner.invoke(cli.site, render_command)

        assert result.exit_code == 0
        mock_yaml.dump_all.assert_called_once()


class TestRepoCliActions(BaseCLIActionTest):
    """Tests repo-level CLI actions."""

    ### Lint tests ###

    def test_lint_repo_using_remote_repo_url_with_exclude(self):
        """Validates repo lint action using remote repo URL."""
        # Scenario:
        #
        # 1) Mock out Deckhand render (so we can ignore P005 issues)
        # 2) Lint repo with exclude flags (should clone repo automatically)

        repo_url = 'https://github.com/openstack/%s@%s' % (self.repo_name,
                                                           self.repo_rev)

        lint_command = ['-r', repo_url, 'lint']
        exclude_lint_command = [
            '-x', errorcodes.SCHEMA_STORAGE_POLICY_MISMATCH_FLAG, '-x',
            errorcodes.SECRET_NOT_ENCRYPTED_POLICY
        ]

        with mock.patch('pegleg.engine.site.util.deckhand') as mock_deckhand:
            mock_deckhand.deckhand_render.return_value = ([], [])
            result = self.runner.invoke(cli.repo,
                                        lint_command + exclude_lint_command)

        assert result.exit_code == 0
        # A successful result (while setting lint checks to exclude) should
        # output nothing.
        assert not result.output

    def test_lint_repo_using_local_path_with_exclude(self):
        """Validates repo lint action using local repo path."""
        # Scenario:
        #
        # 1) Mock out Deckhand render (so we can ignore P005 issues)
        # 2) Lint repo with exclude flags (should skip clone repo)

        repo_path = self.treasuremap_path
        lint_command = ['-r', repo_path, 'lint']
        exclude_lint_command = [
            '-x', errorcodes.SCHEMA_STORAGE_POLICY_MISMATCH_FLAG, '-x',
            errorcodes.SECRET_NOT_ENCRYPTED_POLICY
        ]

        with mock.patch('pegleg.engine.site.util.deckhand') as mock_deckhand:
            mock_deckhand.deckhand_render.return_value = ([], [])
            result = self.runner.invoke(cli.repo,
                                        lint_command + exclude_lint_command)

        assert result.exit_code == 0
        # A successful result (while setting lint checks to exclude) should
        # output nothing.
        assert not result.output

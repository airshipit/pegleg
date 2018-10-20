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
import shutil
import tempfile

from click.testing import CliRunner
import mock
import pytest

from pegleg import cli
from pegleg.engine import errorcodes
from pegleg.engine.util import git
from tests.unit import test_utils
from tests.unit.fixtures import temp_clone_path

@pytest.mark.skipif(
    not test_utils.is_connected(),
    reason='git clone requires network connectivity.')
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


class TestSiteCLIOptions(BaseCLIActionTest):
    """Tests site-level CLI options."""

    ### clone_path tests ###

    def test_list_sites_using_remote_repo_and_clone_path_option(
        self,
        temp_clone_path):
        """Validates clone_path (-p) option is working properly with site list
        action when using remote repo. Verify that the repo was cloned in the
        clone_path
        """
        # Scenario:
        #
        # 1) List sites (should clone repo automatically to `clone_path`
        #    location if `clone_path` is set)

        repo_url = 'https://github.com/openstack/%s@%s' % (self.repo_name,
                                                           self.repo_rev)

        # Note that the -p option is used to specify the clone_folder
        site_list = self.runner.invoke(cli.site, ['-p', temp_clone_path,
                                                  '-r', repo_url, 'list'])

        assert site_list.exit_code == 0
        # Verify that the repo was cloned into the clone_path
        assert os.path.exists(os.path.join(temp_clone_path,
            self.repo_name))
        assert git.is_repository(os.path.join(temp_clone_path,
            self.repo_name))

    def test_list_sites_using_local_repo_and_clone_path_option(self,
        temp_clone_path):
        """Validates clone_path (-p) option is working properly with site list
        action when using a local repo. Verify that the clone_path has NO
        effect when using a local repo
        """
        # Scenario:
        #
        # 1) List sites (when using local repo there should be not cloning
        # even if the clone_path is passed in)

        repo_path = self.treasuremap_path

        # Note that the -p option is used to specify the clone_folder
        site_list = self.runner.invoke(cli.site, ['-p', temp_clone_path,
                                                  '-r', repo_path, 'list'])

        assert site_list.exit_code == 0
        # Verify that passing in clone_path when using local repo has no effect
        assert not os.path.exists(os.path.join(temp_clone_path, self.repo_name))


class TestSiteCLIOptionsNegative(BaseCLIActionTest):
    """Negative Tests for site-level CLI options."""

    ### Negative clone_path tests ###

    def test_list_sites_using_remote_repo_and_reuse_clone_path_option(self,
        temp_clone_path):
        """Validates clone_path (-p) option is working properly with site list
        action when using remote repo. Verify that the same repo can't be
        cloned in the same clone_path if it already exists
        """
        # Scenario:
        #
        # 1) List sites (should clone repo automatically to `clone_path`
        #    location if `clone_path` is set)

        repo_url = 'https://github.com/openstack/%s@%s' % (self.repo_name,
                                                           self.repo_rev)

        # Note that the -p option is used to specify the clone_folder
        site_list = self.runner.invoke(cli.site, ['-p', temp_clone_path,
                                                  '-r', repo_url, 'list'])

        assert git.is_repository(os.path.join(temp_clone_path,
            self.repo_name))

        # Run site list for a second time to validate that the repo can't be
        # cloned twice in the same clone_path
        site_list = self.runner.invoke(cli.site, ['-p', temp_clone_path,
                                                  '-r', repo_url, 'list'])

        assert site_list.exit_code == 1
        msg = "The repository already exists in the given path. Either " \
              "provide a new clone path or pass in the path of the local " \
              "repository as the site repository (-r)."
        assert msg in site_list.output

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

        assert result.exit_code == 0, result.output
        assert len(collected_files) == 1
        # Validates that site manifests collected from cloned repositories
        # are written out to sensibly named files like airship-treasuremap.yaml
        assert collected_files[0] == ("%s.yaml" % self.repo_name)

    def test_collect_using_remote_repo_url_ending_with_dot_git(self):
        """Validates collect action using a remote URL ending in .git."""
        # Scenario:
        #
        # 1) Create temporary save location
        # 2) Collect into save location (should clone repo automatically)
        # 3) Check that expected file name is there

        save_location = tempfile.mkdtemp()
        repo_url = 'https://github.com/openstack/%s@%s.git' % (self.repo_name,
                                                               self.repo_rev)
        result = self.runner.invoke(
            cli.site,
            ['-r', repo_url, 'collect', self.site_name, '-s', save_location])

        collected_files = os.listdir(save_location)

        assert result.exit_code == 0
        assert len(collected_files) == 1
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

        assert result.exit_code == 0, result.output
        assert len(collected_files) == 1
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

        assert result.exit_code == 0, result.output
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

        assert result.exit_code == 0, result.output
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

        assert result.exit_code == 0, result.output
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

        # Mock out PrettyTable to determine output.
        with mock.patch('pegleg.engine.site.PrettyTable') as mock_writer:
            result = self.runner.invoke(cli.site, ['-r', repo_url, 'list'])

        m_writer = mock_writer.return_value
        m_writer.add_row.assert_called_with([self.site_name, 'foundry'])

    def test_list_sites_using_local_path(self):
        """Validates list action using local repo path."""
        # Scenario:
        #
        # 1) List sites (should skip clone repo)

        repo_path = self.treasuremap_path

        # Mock out PrettyTable to determine output.
        with mock.patch('pegleg.engine.site.PrettyTable') as mock_writer:
            result = self.runner.invoke(cli.site, ['-r', repo_path, 'list'])

        m_writer = mock_writer.return_value
        m_writer.add_row.assert_called_with([self.site_name, 'foundry'])

    ### Show tests ###

    def test_show_site_using_remote_repo_url(self):
        """Validates show action using remote repo URL."""
        # Scenario:
        #
        # 1) Show site (should clone repo automatically)

        repo_url = 'https://github.com/openstack/%s@%s' % (self.repo_name,
                                                           self.repo_rev)

        with mock.patch('pegleg.engine.site.PrettyTable') as mock_writer:
            result = self.runner.invoke(
                cli.site, ['-r', repo_url, 'show', self.site_name])

        m_writer = mock_writer.return_value
        m_writer.add_row.assert_called_with(
            ['', self.site_name, 'foundry', mock.ANY])

    def test_show_site_using_local_path(self):
        """Validates show action using local repo path."""
        # Scenario:
        #
        # 1) Show site (should skip clone repo)

        repo_path = self.treasuremap_path
        with mock.patch('pegleg.engine.site.PrettyTable') as mock_writer:
            result = self.runner.invoke(
                cli.site, ['-r', repo_path, 'show', self.site_name])

        m_writer = mock_writer.return_value
        m_writer.add_row.assert_called_with(
            ['', self.site_name, 'foundry', mock.ANY])

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

        assert result.exit_code == 0, result.output
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

        assert result.exit_code == 0, result.output
        # A successful result (while setting lint checks to exclude) should
        # output nothing.
        assert not result.output


class TestTypeCliActions(BaseCLIActionTest):
    """Tests type-level CLI actions."""

    def setup(self):
        self.expected_types = ['foundry']

    def _assert_table_has_expected_sites(self, mock_output):
        output_table = mock_output.write.mock_calls[0][1][0]
        for expected_type in self.expected_types:
            assert expected_type in output_table

    def _validate_type_list_action(self, repo_path_or_url):
        mock_output = mock.Mock()
        result = self.runner.invoke(
            cli.type, ['-r', repo_path_or_url, 'list', '-o', mock_output])

        assert result.exit_code == 0, result.output
        self._assert_table_has_expected_sites(mock_output)

    def test_list_types_using_remote_repo_url(self):
        """Validates list types action using remote repo URL."""
        # Scenario:
        #
        # 1) List types (should clone repo automatically)

        repo_url = 'https://github.com/openstack/%s@%s' % (self.repo_name,
                                                           self.repo_rev)
        self._validate_type_list_action(repo_url)

    def test_list_types_using_local_repo_path(self):
        """Validates list types action using local repo path."""
        # Scenario:
        #
        # 1) List types for local repo path

        repo_path = self.treasuremap_path
        self._validate_type_list_action(repo_path)


class TestSiteCliActionsWithSubdirectory(BaseCLIActionTest):
    """Tests site CLI actions with subdirectories in repository paths."""

    def setup(self):
        self.expected_sites = ['demo', 'gate-multinode', 'dev', 'dev-proxy']

    def _assert_table_has_expected_sites(self, mock_output):
        output_table = mock_output.write.mock_calls[0][1][0]
        for expected_site in self.expected_sites:
            assert expected_site in output_table

    def _validate_site_action(self, repo_path_or_url):
        mock_output = mock.Mock()
        result = self.runner.invoke(
            cli.site, ['-r', repo_path_or_url, 'list', '-o', mock_output])

        assert result.exit_code == 0, result.output
        self._assert_table_has_expected_sites(mock_output)

    def test_site_action_with_subpath_in_remote_url(self):
        """Validates list action with subpath in remote URL."""
        # Scenario:
        #
        # 1) List sites for https://github.com/airship-in-a-bottle/
        #    deployment_files (subpath in remote URL)

        # Perform site action using remote URL.
        repo_name = 'airship-in-a-bottle'
        repo_rev = '7a0717adc68261c7adb3a3db74a9326d6103519f'
        repo_url = 'https://github.com/openstack/%s/deployment_files@%s' % (
            repo_name, repo_rev)

        self._validate_site_action(repo_url)

    def test_site_action_with_subpath_in_local_repo_path(self):
        """Validates list action with subpath in local repo path."""
        # Scenario:
        #
        # 1) List sites for local repo at /tmp/.../airship-in-a-bottle/
        #    deployment_files

        # Perform site action using local repo path.
        repo_name = 'airship-in-a-bottle'
        repo_rev = '7a0717adc68261c7adb3a3db74a9326d6103519f'
        repo_url = 'https://github.com/openstack/%s' % repo_name
        _repo_path = git.git_handler(repo_url, ref=repo_rev)
        repo_path = os.path.join(_repo_path, 'deployment_files')

        self._validate_site_action(repo_path)

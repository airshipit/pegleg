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
import glob
import os
import subprocess
from unittest import mock

from click.testing import CliRunner
import pytest
import yaml

from pegleg import pegleg_main
from pegleg.cli import commands
from pegleg.engine import errorcodes
from pegleg.engine.catalog import pki_utility
from pegleg.engine.util import git
from tests.unit import test_utils

TEST_PARAMS = {
    "site_name": "seaworthy",
    "site_type": "foundry",
    "repo_rev": '29c67eb3a0ce046e41cfadbb9381697cd556f659',
    "repo_name": "treasuremap",
    "repo_url": "https://opendev.org/airship/treasuremap.git",
}

TEST_CERT = """
-----BEGIN CERTIFICATE-----

DEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEF
DEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEF
DEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEF
DEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEFDEADBEEF

-----END CERTIFICATE-----
"""


@pytest.mark.skipif(
    not test_utils.is_connected(),
    reason='git clone requires network connectivity.')
class BaseCLIActionTest(object):
    """Tests end-to-end flows for all Pegleg CLI actions, with minimal mocking.

    General pattern should be to include exactly one test that uses a remote
    repo URL and as many other tests that are required that use a local repo
    path for runtime optimization.

    All tests should validate that the ``exit_code`` from the CLI is 0 (for
    positive tests).

    """

    # TODO(felipemonteiro): Need tests that validate repository overrides. Also
    # need to write tests that use a site-defintion.yaml with repositories key.

    @classmethod
    def setup_class(cls):
        cls.runner = CliRunner()

        # Pin so we know that seaworthy is a valid site.
        cls.site_name = TEST_PARAMS["site_name"]
        cls.site_type = TEST_PARAMS["site_type"]

        cls.repo_rev = TEST_PARAMS["repo_rev"]
        cls.repo_name = TEST_PARAMS["repo_name"]
        cls.treasuremap_path = git.git_handler(
            TEST_PARAMS["repo_url"], ref=TEST_PARAMS["repo_rev"])


class TestSiteCLIOptions(BaseCLIActionTest):
    """Tests site-level CLI options."""

    ### clone_path tests ###

    def test_list_sites_using_remote_repo_and_clone_path_option(self, tmpdir):
        """Validates clone_path (-p) option is working properly with site list
        action when using remote repo. Verify that the repo was cloned in the
        clone_path
        """
        # Scenario:
        #
        # 1) List sites (should clone repo automatically to `clone_path`
        #    location if `clone_path` is set)

        repo_url = 'https://opendev.org/airship/%s@%s' % (
            self.repo_name, self.repo_rev)

        # Note that the -p option is used to specify the clone_folder
        site_list = self.runner.invoke(
            commands.site,
            ['--no-decrypt', '-p', tmpdir, '-r', repo_url, 'list'])

        assert site_list.exit_code == 0
        # Verify that the repo was cloned into the clone_path
        assert os.path.exists(os.path.join(tmpdir, self.repo_name))
        assert git.is_repository(os.path.join(tmpdir, self.repo_name))

    def test_list_sites_using_local_repo_and_clone_path_option(self, tmpdir):
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
        site_list = self.runner.invoke(
            commands.site,
            ['--no-decrypt', '-p', tmpdir, '-r', repo_path, 'list'])

        assert site_list.exit_code == 0
        # Verify that passing in clone_path when using local repo has no effect
        assert not os.path.exists(os.path.join(tmpdir, self.repo_name))


class TestSiteCLIOptionsNegative(BaseCLIActionTest):
    """Negative Tests for site-level CLI options."""

    ### Negative clone_path tests ###

    def test_list_sites_using_remote_repo_and_reuse_clone_path_option(
            self, tmpdir):
        """Validates clone_path (-p) option is working properly with site list
        action when using remote repo. Verify that the same repo can't be
        cloned in the same clone_path if it already exists
        """
        # Scenario:
        #
        # 1) List sites (should clone repo automatically to `clone_path`
        #    location if `clone_path` is set)

        repo_url = 'https://opendev.org/airship/%s@%s' % (
            self.repo_name, self.repo_rev)

        # Note that the -p option is used to specify the clone_folder
        site_list = self.runner.invoke(
            commands.site,
            ['--no-decrypt', '-p', tmpdir, '-r', repo_url, 'list'])

        assert git.is_repository(os.path.join(tmpdir, self.repo_name))

        # Run site list for a second time to validate that the repo can't be
        # cloned twice in the same clone_path
        site_list = self.runner.invoke(
            commands.site,
            ['--no-decrypt', '-p', tmpdir, '-r', repo_url, 'list'])

        assert site_list.exit_code == 1
        assert 'File exists' in site_list.output


class TestSiteCliActions(BaseCLIActionTest):
    """Tests site-level CLI actions."""

    ### Collect tests ###

    def _validate_collect_site_action(self, repo_path_or_url, save_location):
        result = self.runner.invoke(
            commands.site, [
                '--no-decrypt', '-r', repo_path_or_url, 'collect',
                self.site_name, '-s', save_location
            ])

        collected_files = os.listdir(save_location)

        assert result.exit_code == 0, result.output
        assert len(collected_files) == 1
        # Validates that site manifests collected from cloned repositories
        # are written out to sensibly named files like airship-treasuremap.yaml
        assert collected_files[0] == ("%s.yaml" % self.repo_name)

    def test_collect_using_remote_repo_url(self, tmpdir):
        """Validates collect action using a remote URL."""
        # Scenario:
        #
        # 1) Create temporary save location
        # 2) Collect into save location (should clone repo automatically)
        # 3) Check that expected file name is there

        repo_url = 'https://opendev.org/airship/%s@%s' % (
            self.repo_name, self.repo_rev)
        self._validate_collect_site_action(repo_url, tmpdir)

    def test_collect_using_remote_repo_url_ending_with_dot_git(self, tmpdir):
        """Validates collect action using a remote URL ending in .git."""
        # Scenario:
        #
        # 1) Create temporary save location
        # 2) Collect into save location (should clone repo automatically)
        # 3) Check that expected file name is there

        repo_url = 'https://opendev.org/airship/%s@%s.git' % (
            self.repo_name, self.repo_rev)
        self._validate_collect_site_action(repo_url, tmpdir)

    def test_collect_using_local_path(self, tmpdir):
        """Validates collect action using a path to a local repo."""
        # Scenario:
        #
        # 1) Create temporary save location
        # 2) Collect into save location (should skip clone repo)
        # 3) Check that expected file name is there

        repo_path = self.treasuremap_path
        self._validate_collect_site_action(repo_path, tmpdir)

    ### Lint tests ###

    def _test_lint_site_action(self, repo_path_or_url, exclude=True):
        flag = '-x' if exclude else '-w'

        lint_command = [
            '--no-decrypt', '-r', repo_path_or_url, 'lint', self.site_name
        ]
        exclude_lint_command = [
            flag, errorcodes.SCHEMA_STORAGE_POLICY_MISMATCH_FLAG, flag,
            errorcodes.SECRET_NOT_ENCRYPTED_POLICY
        ]

        with mock.patch('pegleg.engine.site.util.deckhand') as mock_deckhand:
            mock_deckhand.deckhand_render.return_value = ([], [])
            result = self.runner.invoke(
                commands.site, lint_command + exclude_lint_command)

        assert result.exit_code == 0, result.output

        if exclude:
            # A successful result (while setting lint checks to exclude) should
            # output nothing.
            assert not result.output
        else:
            assert result.output

    def test_lint_site_using_remote_repo_url_with_exclude(self):
        """Validates site lint action using remote repo URL."""
        # Scenario:
        #
        # 1) Mock out Deckhand render (so we can ignore P005 issues)
        # 2) Lint site with exclude flags (should clone repo automatically)

        repo_url = 'https://opendev.org/airship/%s@%s' % (
            self.repo_name, self.repo_rev)
        self._test_lint_site_action(repo_url, exclude=True)

    def test_lint_site_using_local_path_with_exclude(self):
        """Validates site lint action using local repo path."""
        # Scenario:
        #
        # 1) Mock out Deckhand render (so we can ignore P005 issues)
        # 2) Lint site with exclude flags (should skip clone repo)

        repo_path = self.treasuremap_path
        self._test_lint_site_action(repo_path, exclude=True)

    def test_lint_site_using_local_path_with_warn(self):
        """Validates site lint action using local repo path."""
        # Scenario:
        #
        # 1) Mock out Deckhand render (so we can ignore P005 issues)
        # 2) Lint site with warn flags (should skip clone repo)

        repo_path = self.treasuremap_path
        self._test_lint_site_action(repo_path, exclude=False)

    ### List tests ###

    def _validate_list_site_action(self, repo_path_or_url, tmpdir):
        mock_output = os.path.join(tmpdir, 'output')
        result = self.runner.invoke(
            commands.site, [
                '--no-decrypt', '-r', repo_path_or_url, 'list', '-o',
                mock_output
            ])

        assert result.exit_code == 0, result.output
        with open(mock_output, 'r') as f:
            table_output = f.read()
        assert self.site_name in table_output
        assert self.site_type in table_output

    def test_list_sites_using_remote_repo_url(self, tmpdir):
        """Validates list action using remote repo URL."""
        # Scenario:
        #
        # 1) List sites (should clone repo automatically)

        repo_url = 'https://opendev.org/airship/%s@%s' % (
            self.repo_name, self.repo_rev)

        self._validate_list_site_action(repo_url, tmpdir)

    def test_list_sites_using_local_path(self, tmpdir):
        """Validates list action using local repo path."""
        # Scenario:
        #
        # 1) List sites (should skip clone repo)

        repo_path = self.treasuremap_path
        self._validate_list_site_action(repo_path, tmpdir)

    ### Show tests ###

    def _validate_site_show_action(self, repo_path_or_url, tmpdir):
        mock_output = os.path.join(tmpdir, 'output')
        result = self.runner.invoke(
            commands.site, [
                '--no-decrypt', '-r', repo_path_or_url, 'show', self.site_name,
                '-o', mock_output
            ])

        assert result.exit_code == 0, result.output
        with open(mock_output, 'r') as f:
            table_output = f.read()
        assert self.site_name in table_output

    def test_show_site_using_remote_repo_url(self, tmpdir):
        """Validates show action using remote repo URL."""
        # Scenario:
        #
        # 1) Show site (should clone repo automatically)

        repo_url = 'https://opendev.org/airship/%s@%s' % (
            self.repo_name, self.repo_rev)
        self._validate_site_show_action(repo_url, tmpdir)

    def test_show_site_using_local_path(self, tmpdir):
        """Validates show action using local repo path."""
        # Scenario:
        #
        # 1) Show site (should skip clone repo)

        repo_path = self.treasuremap_path
        self._validate_site_show_action(repo_path, tmpdir)

    ### Render tests ###

    def _validate_render_site_action(self, repo_path_or_url):
        render_command = [
            '--no-decrypt', '-r', repo_path_or_url, 'render', self.site_name
        ]

        with mock.patch('pegleg.engine.site.yaml') as mock_yaml:
            with mock.patch(
                    'pegleg.engine.site.util.deckhand') as mock_deckhand:
                mock_deckhand.deckhand_render.return_value = ([], [])
                result = self.runner.invoke(commands.site, render_command)

        assert result.exit_code == 0
        mock_yaml.dump_all.assert_called_once()

    def test_render_site_using_remote_repo_url(self):
        """Validates render action using remote repo URL."""
        # Scenario:
        #
        # 1) Mock out Deckhand render (so we can ignore P005 issues)
        # 2) Render site (should clone repo automatically)

        repo_url = 'https://opendev.org/airship/%s@%s' % (
            self.repo_name, self.repo_rev)
        self._validate_render_site_action(repo_url)

    def test_render_site_using_local_path(self):
        """Validates render action using local repo path."""
        # Scenario:
        #
        # 1) Mock out Deckhand render (so we can ignore P005 issues)
        # 2) Render site (should skip clone repo)

        repo_path = self.treasuremap_path
        self._validate_render_site_action(repo_path)

    ### Upload tests ###
    @mock.patch.dict(
        os.environ, {
            "PEGLEG_PASSPHRASE": "123456789012345678901234567890",
            "PEGLEG_SALT": "MySecretSalt1234567890]["
        })
    def test_upload_documents_shipyard_using_local_repo_path(self):
        """Validates ShipyardHelper is called with correct arguments."""
        # Scenario:
        #
        # 1) Mock out ShipyardHelper
        # 2) Check ShipyardHelper was called with correct arguments

        repo_path = self.treasuremap_path

        with mock.patch('pegleg.pegleg_main.ShipyardHelper') as mock_obj:
            result = self.runner.invoke(
                commands.site, [
                    '--no-decrypt', '-r', repo_path, 'upload', self.site_name,
                    '--collection', 'collection'
                ])

        assert result.exit_code == 0
        mock_obj.assert_called_once()

    @mock.patch.dict(
        os.environ, {
            "PEGLEG_PASSPHRASE": "123456789012345678901234567890",
            "PEGLEG_SALT": "MySecretSalt1234567890]["
        })
    def test_upload_collection_callback_default_to_site_name(self):
        """Validates that collection will default to the given site_name"""
        # Scenario:
        #
        # 1) Mock out ShipyardHelper
        # 2) Check that ShipyardHelper was called with collection set to
        #    site_name
        repo_path = self.treasuremap_path

        with mock.patch('pegleg.pegleg_main.ShipyardHelper') as mock_obj:
            result = self.runner.invoke(
                commands.site,
                ['--no-decrypt', '-r', repo_path, 'upload', self.site_name])
        assert result.exit_code == 0
        mock_obj.assert_called_once()


class TestGenerateActions(BaseCLIActionTest):
    def test_generate_passphrase(self):
        result = self.runner.invoke(commands.generate, ['passphrase'])

        assert result.exit_code == 0, result.output

    def test_generate_salt(self):
        result = self.runner.invoke(commands.generate, ['salt'])

        assert result.exit_code == 0, result.output


class TestRepoCliActions(BaseCLIActionTest):
    """Tests repo-level CLI actions."""

    ### Lint tests ###

    def test_lint_repo_using_remote_repo_url_with_exclude(self):
        """Validates repo lint action using remote repo URL."""
        # Scenario:
        #
        # 1) Mock out Deckhand render (so we can ignore P005 issues)
        # 2) Lint repo with exclude flags (should clone repo automatically)

        repo_url = 'https://opendev.org/airship/%s@%s' % (
            self.repo_name, self.repo_rev)

        lint_command = ['-r', repo_url, 'lint']
        exclude_lint_command = [
            '-x', errorcodes.SCHEMA_STORAGE_POLICY_MISMATCH_FLAG, '-x',
            errorcodes.SECRET_NOT_ENCRYPTED_POLICY
        ]

        with mock.patch('pegleg.engine.site.util.deckhand') as mock_deckhand:
            mock_deckhand.deckhand_render.return_value = ([], [])
            result = self.runner.invoke(
                commands.repo, lint_command + exclude_lint_command)

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
            result = self.runner.invoke(
                commands.repo, lint_command + exclude_lint_command)

        assert result.exit_code == 0, result.output
        # A successful result (while setting lint checks to exclude) should
        # output nothing.
        assert not result.output


class TestSiteSecretsActions(BaseCLIActionTest):
    """Tests site secrets-related CLI actions."""
    @classmethod
    def setup_class(cls):
        super(TestSiteSecretsActions, cls).setup_class()
        cls.runner = CliRunner(
            env={
                "PEGLEG_PASSPHRASE": 'ytrr89erARAiPE34692iwUMvWqqBvC',
                "PEGLEG_SALT": "MySecretSalt1234567890]["
            })

    def _validate_generate_pki_action(self, result):
        assert result.exit_code == 0

        generated_files = []
        output_lines = result.output.split("\n")
        for line in output_lines:
            if self.repo_name in line:
                generated_files.append(line)

        assert len(generated_files), 'No secrets were generated'
        for generated_file in generated_files:
            with open(generated_file, 'r') as f:
                result = yaml.safe_load_all(f)  # Validate valid YAML.
                assert list(result), "%s file is empty" % generated_file

    @pytest.mark.skipif(
        not pki_utility.PKIUtility.cfssl_exists(),
        reason='cfssl must be installed to execute these tests')
    def test_site_secrets_generate_pki_using_remote_repo_url(self):
        """Validates ``generate certificates`` action using remote repo URL."""
        # Scenario:
        #
        # 1) Generate PKI using remote repo URL

        repo_url = 'https://opendev.org/airship/%s@%s' % (
            self.repo_name, self.repo_rev)

        secrets_opts = ['secrets', 'generate', 'certificates', self.site_name]

        result = self.runner.invoke(
            commands.site, ['--no-decrypt', '-r', repo_url] + secrets_opts)
        self._validate_generate_pki_action(result)

    @pytest.mark.skipif(
        not pki_utility.PKIUtility.cfssl_exists(),
        reason='cfssl must be installed to execute these tests')
    def test_site_secrets_generate_pki_using_local_repo_path(self):
        """Validates ``generate certificates`` action using local repo path."""
        # Scenario:
        #
        # 1) Generate PKI using local repo path

        repo_path = self.treasuremap_path
        secrets_opts = ['secrets', 'generate', 'certificates', self.site_name]

        result = self.runner.invoke(
            commands.site, ['--no-decrypt', '-r', repo_path] + secrets_opts)
        self._validate_generate_pki_action(result)

    @pytest.mark.skipif(
        not pki_utility.PKIUtility.cfssl_exists(),
        reason='cfssl must be installed to execute these tests')
    @mock.patch.dict(
        os.environ, {
            "PEGLEG_PASSPHRASE": "123456789012345678901234567890",
            "PEGLEG_SALT": "MySecretSalt1234567890]["
        })
    def test_site_secrets_encrypt_and_decrypt_local_repo_path(self):
        """Validates ``generate certificates`` action using local repo path."""
        # Scenario:
        #
        # 1) Encrypt a file in a local repo

        repo_path = self.treasuremap_path
        file_path = os.path.join(
            repo_path, "site", "seaworthy", "secrets", "passphrases",
            "ceph_fsid.yaml")
        with open(file_path, "r") as ceph_fsid_fi:
            ceph_fsid = yaml.safe_load(ceph_fsid_fi)
            ceph_fsid["metadata"]["storagePolicy"] = "encrypted"
            ceph_fsid["metadata"]["layeringDefinition"]["layer"] = "site"

        with open(file_path, "w") as ceph_fsid_fi:
            yaml.dump(ceph_fsid, ceph_fsid_fi)

        secrets_opts = ['secrets', 'encrypt', '-a', 'test', self.site_name]
        result = self.runner.invoke(
            commands.site, ['--no-decrypt', '-r', repo_path] + secrets_opts)

        assert result.exit_code == 0

        with open(os.path.join(repo_path, "site", "seaworthy",
                               "secrets", "passphrases", "ceph_fsid.yaml"),
                  "r") \
                as ceph_fsid_fi:
            ceph_fsid = yaml.safe_load(ceph_fsid_fi)
            assert "encrypted" in ceph_fsid["data"]
            assert "managedDocument" in ceph_fsid["data"]

        secrets_opts = [
            'secrets', 'decrypt', '--path', file_path, self.site_name
        ]
        result = self.runner.invoke(
            commands.site, ['--no-decrypt', '-r', repo_path] + secrets_opts)
        assert result.exit_code == 0, result.output

    @pytest.mark.skipif(
        not pki_utility.PKIUtility.cfssl_exists(),
        reason='cfssl must be installed to execute these tests')
    def test_check_pki_certs_expired(self):
        repo_path = self.treasuremap_path
        secrets_opts = ['secrets', 'check-pki-certs', self.site_name]
        result = self.runner.invoke(
            commands.site, ['--no-decrypt', '-r', repo_path] + secrets_opts)
        assert result.exit_code == 1, result.output

    @pytest.mark.skipif(
        not pki_utility.PKIUtility.cfssl_exists(),
        reason='cfssl must be installed to execute these tests')
    def test_check_pki_certs(self):
        repo_path = self.treasuremap_path
        secrets_opts = ['secrets', 'check-pki-certs', 'airsloop']
        result = self.runner.invoke(
            commands.site, ['--no-decrypt', '-r', repo_path] + secrets_opts)
        assert result.exit_code == 0, result.output

    @mock.patch.dict(
        os.environ, {
            "PEGLEG_PASSPHRASE": "123456789012345678901234567890",
            "PEGLEG_SALT": "123456"
        })
    def test_site_secrets_wrap(self):
        """Validates ``generate certificates`` action using local repo path."""
        # Scenario:
        #
        # 1) Encrypt a file in a local repo

        repo_path = self.treasuremap_path
        file_dir = os.path.join(
            repo_path, "site", "seaworthy", "secrets", "certificates")
        file_path = os.path.join(file_dir, "test.crt")
        output_path = os.path.join(file_dir, "test.yaml")

        with open(file_path, "w") as test_crt_fi:
            test_crt_fi.write(TEST_CERT)
        secrets_opts = [
            'secrets', 'wrap', "-a", "lm734y", "--filename", file_path, "-s",
            "deckhand/Certificate/v1", "-n", "test-certificate", "-l", "site",
            "--no-encrypt", self.site_name
        ]
        result = self.runner.invoke(
            commands.site, ['--no-decrypt', "-r", repo_path] + secrets_opts)
        assert result.exit_code == 0

        with open(output_path, "r") as output_fi:
            doc = yaml.safe_load(output_fi)
            assert doc["data"]["managedDocument"]["data"] == TEST_CERT
            assert doc["data"]["managedDocument"][
                "schema"] == "deckhand/Certificate/v1"
            assert doc["data"]["managedDocument"]["metadata"][
                "name"] == "test-certificate"
            assert doc["data"]["managedDocument"]["metadata"][
                "layeringDefinition"]["layer"] == "site"
            assert doc["data"]["managedDocument"]["metadata"][
                "storagePolicy"] == "cleartext"

        os.remove(output_path)
        secrets_opts = [
            'secrets', 'wrap', "-a", "lm734y", "--filename", file_path, "-o",
            output_path, "-s", "deckhand/Certificate/v1", "-n",
            "test-certificate", "-l", "site", self.site_name
        ]
        result = self.runner.invoke(
            commands.site, ['--no-decrypt', "-r", repo_path] + secrets_opts)
        assert result.exit_code == 0

        with open(output_path, "r") as output_fi:
            doc = yaml.safe_load(output_fi)
            assert "encrypted" in doc["data"]
            assert "managedDocument" in doc["data"]


class TestTypeCliActions(BaseCLIActionTest):
    """Tests type-level CLI actions."""
    def setup(self):
        self.expected_types = ['foundry']

    def _assert_table_has_expected_sites(self, table_output):
        for expected_type in self.expected_types:
            assert expected_type in table_output

    def _validate_type_list_action(self, repo_path_or_url, tmpdir):
        mock_output = os.path.join(tmpdir, 'output')
        result = self.runner.invoke(
            commands.type, ['-r', repo_path_or_url, 'list', '-o', mock_output])
        with open(mock_output, 'r') as f:
            table_output = f.read()

        assert result.exit_code == 0, result.output
        self._assert_table_has_expected_sites(table_output)

    def test_list_types_using_remote_repo_url(self, tmpdir):
        """Validates list types action using remote repo URL."""
        # Scenario:
        #
        # 1) List types (should clone repo automatically)

        repo_url = 'https://opendev.org/airship/%s@%s' % (
            self.repo_name, self.repo_rev)
        self._validate_type_list_action(repo_url, tmpdir)

    def test_list_types_using_local_repo_path(self, tmpdir):
        """Validates list types action using local repo path."""
        # Scenario:
        #
        # 1) List types for local repo path

        repo_path = self.treasuremap_path
        self._validate_type_list_action(repo_path, tmpdir)


class TestSiteCliActionsWithSubdirectory(BaseCLIActionTest):
    """Tests site CLI actions with subdirectories in repository paths."""
    def setup(self):
        self.expected_sites = ['demo', 'gate-multinode', 'dev', 'dev-proxy']

    def _assert_table_has_expected_sites(self, table_output):
        for expected_site in self.expected_sites:
            assert expected_site in table_output

    def _validate_list_site_action(self, repo_path_or_url, tmpdir):
        mock_output = os.path.join(tmpdir, 'output')
        result = self.runner.invoke(
            commands.site, [
                '--no-decrypt', '-r', repo_path_or_url, 'list', '-o',
                mock_output
            ])

        with open(mock_output, 'r') as f:
            table_output = f.read()

        assert result.exit_code == 0, result.output
        self._assert_table_has_expected_sites(table_output)

    def test_site_action_with_subpath_in_remote_url(self, tmpdir):
        """Validates list action with subpath in remote URL."""
        # Scenario:
        #
        # 1) List sites for https://opendev.org/airship/airship-in-a-bottle
        #    deployment_files (subpath in remote URL)

        # Perform site action using remote URL.
        repo_name = 'airship-in-a-bottle'
        repo_rev = '7a0717adc68261c7adb3a3db74a9326d6103519f'
        repo_url = 'https://opendev.org/airship/%s/deployment_files@%s' % (
            repo_name, repo_rev)

        self._validate_list_site_action(repo_url, tmpdir)

    def test_site_action_with_subpath_in_local_repo_path(self, tmpdir):
        """Validates list action with subpath in local repo path."""
        # Scenario:
        #
        # 1) List sites for local repo at /tmp/.../airship-in-a-bottle/
        #    deployment_files

        # Perform site action using local repo path.
        repo_name = 'airship-in-a-bottle'
        repo_rev = '7a0717adc68261c7adb3a3db74a9326d6103519f'
        repo_url = 'https://opendev.org/airship/%s' % repo_name
        _repo_path = git.git_handler(repo_url, ref=repo_rev)
        repo_path = os.path.join(_repo_path, 'deployment_files')

        self._validate_list_site_action(repo_path, tmpdir)


@pytest.mark.usefixtures('monkeypatch')
class TestCliSiteSubcommandsWithDecryptOption(BaseCLIActionTest):
    @classmethod
    def setup_class(cls):
        super(TestCliSiteSubcommandsWithDecryptOption, cls).setup_class()
        cls.runner = CliRunner(
            env={
                "PEGLEG_PASSPHRASE": 'ytrr89erARAiPE34692iwUMvWqqBvC',
                "PEGLEG_SALT": "MySecretSalt1234567890][",
                "PROMENADE_ENCRYPTION_KEY": "test"
            })
        for file in glob.iglob(os.path.join(cls.treasuremap_path, 'site',
                                            'seaworthy', 'secrets', '**',
                                            '*.yaml'), recursive=True):
            args = [
                'sed', '-i',
                's/storagePolicy: cleartext/storagePolicy: encrypted/g', file
            ]
            sed_output = subprocess.check_output(args, shell=False)
            assert not sed_output

    @mock.patch.dict(
        os.environ, {
            "PEGLEG_PASSPHRASE": 'ytrr89erARAiPE34692iwUMvWqqBvC',
            "PEGLEG_SALT": "MySecretSalt1234567890]["
        })
    def setup(self):
        pegleg_main.run_config(
            self.treasuremap_path, None, None, None, [], True, False)
        pegleg_main.run_encrypt('zuul-tester', None, self.site_name)

    @staticmethod
    def _validate_no_files_encrypted(path):
        for file in glob.iglob(os.path.join(path, '**', '*.yaml'),
                               recursive=True):
            with open(file, 'r') as f:
                data = f.read()
                if 'pegleg/PeglegManagedDocument/v1' in data:
                    return False
        return True

    def test_collect_using_decrypt_option(self, tmpdir):
        """Validates collect action using a path to a local repo."""
        # Scenario:
        #
        # 1) Create temporary save location
        # 2) Collect into save location (should skip clone repo)
        # 3) Check that expected file name is there

        repo_path = self.treasuremap_path
        result = self.runner.invoke(
            commands.site, [
                '--decrypt', '-r', repo_path, 'collect', self.site_name, '-s',
                tmpdir
            ])

        collected_files = os.listdir(tmpdir)

        assert result.exit_code == 0, result.output
        assert len(collected_files) == 1
        # Validates that site manifests collected from cloned repositories
        # are written out to sensibly named files like airship-treasuremap.yaml
        assert collected_files[0] == ("%s.yaml" % self.repo_name)
        assert self._validate_no_files_encrypted(tmpdir)

    def test_render_site_using_decrypt_option(self, tmpdir):
        """Validates render action using local repo path."""
        # Scenario:
        #
        # 1) Mock out Deckhand render (so we can ignore P005 issues)
        # 2) Render site (should skip clone repo)

        repo_path = self.treasuremap_path
        render_command = [
            '--decrypt', '-p', tmpdir, '-r', repo_path, 'render',
            self.site_name
        ]

        with mock.patch('pegleg.engine.site.yaml') as mock_yaml:
            with mock.patch(
                    'pegleg.engine.site.util.deckhand') as mock_deckhand:
                mock_deckhand.deckhand_render.return_value = ([], [])
                result = self.runner.invoke(commands.site, render_command)

        assert result.exit_code == 0
        mock_yaml.dump_all.assert_called_once()
        assert self._validate_no_files_encrypted(
            os.path.join(
                tmpdir, 'treasuremap.git', 'site', 'seaworthy', 'secrets'))

    def test_lint_site_using_decrypt_option(self, tmpdir):
        """Validates site lint action using local repo path."""
        # Scenario:
        #
        # 1) Mock out Deckhand render (so we can ignore P005 issues)
        # 2) Lint site with warn flags (should skip clone repo)

        repo_path = self.treasuremap_path

        lint_command = [
            '--decrypt', '-p', tmpdir, '-r', repo_path, 'lint', self.site_name
        ]
        exclude_lint_command = [
            '-w', errorcodes.SCHEMA_STORAGE_POLICY_MISMATCH_FLAG, '-w',
            errorcodes.SECRET_NOT_ENCRYPTED_POLICY
        ]

        with mock.patch('pegleg.engine.site.util.deckhand') as mock_deckhand:
            mock_deckhand.deckhand_render.return_value = ([], [])
            result = self.runner.invoke(
                commands.site, lint_command + exclude_lint_command)

        assert result.exit_code == 0, result.output
        assert self._validate_no_files_encrypted(
            os.path.join(
                tmpdir, 'treasuremap.git', 'site', 'seaworthy', 'secrets'))

    @mock.patch.dict(
        os.environ, {
            "PEGLEG_PASSPHRASE": "123456789012345678901234567890",
            "PEGLEG_SALT": "MySecretSalt1234567890]["
        })
    def test_upload_collection_callback_default_to_site_name(self, tmpdir):
        """Validates that collection will default to the given site_name"""
        # Scenario:
        #
        # 1) Mock out ShipyardHelper
        # 2) Check that ShipyardHelper was called with collection set to
        #    site_name
        repo_path = self.treasuremap_path

        with mock.patch('pegleg.pegleg_main.ShipyardHelper') as mock_obj:
            result = self.runner.invoke(
                commands.site, [
                    '--decrypt', '-p', tmpdir, '-r', repo_path, 'upload',
                    self.site_name
                ])
        assert result.exit_code == 0
        mock_obj.assert_called_once()
        assert self._validate_no_files_encrypted(
            os.path.join(
                tmpdir, 'treasuremap.git', 'site', 'seaworthy', 'secrets'))

    @pytest.mark.skipif(
        not pki_utility.PKIUtility.cfssl_exists(),
        reason='cfssl must be installed to execute these tests')
    def test_site_secrets_generate_pki_using_decrypt_option(self, tmpdir):
        """Validates ``generate certificates`` action using local repo path."""
        # Scenario:
        #
        # 1) Generate PKI using local repo path

        repo_path = self.treasuremap_path
        secrets_opts = ['secrets', 'generate', 'certificates', self.site_name]

        result = self.runner.invoke(
            commands.site,
            ['--decrypt', '-p', tmpdir, '-r', repo_path] + secrets_opts)
        assert result.exit_code == 0

        generated_files = []
        output_lines = result.output.split("\n")
        for line in output_lines:
            if self.repo_name in line:
                generated_files.append(line)

        assert len(generated_files), 'No secrets were generated'
        for generated_file in generated_files:
            with open(generated_file, 'r') as f:
                result = yaml.safe_load_all(f)  # Validate valid YAML.
                assert list(result), "%s file is empty" % generated_file
        assert self._validate_no_files_encrypted(
            os.path.join(
                tmpdir, 'treasuremap.git', 'site', 'seaworthy', 'secrets'))

    @pytest.mark.skipif(
        not pki_utility.PKIUtility.cfssl_exists(),
        reason='cfssl must be installed to execute these tests')
    def test_check_pki_certs_expired_using_decrypt_option(self):
        repo_path = self.treasuremap_path
        secrets_opts = ['secrets', 'check-pki-certs', self.site_name]
        result = self.runner.invoke(
            commands.site, ['--decrypt', '-r', repo_path] + secrets_opts)
        assert result.exit_code == 1, result.output
        assert self._validate_no_files_encrypted(
            os.path.join(repo_path, 'site', 'seaworthy', 'secrets'))

    def test_genesis_bundle_using_decrypt_option(self, tmpdir):
        repo_path = self.treasuremap_path
        args = [
            '--decrypt', '-p', tmpdir, '-r', repo_path, 'genesis_bundle', '-b',
            tmpdir, self.site_name
        ]
        with mock.patch(
                'pegleg.pegleg_main.bundle.build_genesis') as mock_build:
            result = self.runner.invoke(commands.site, args)
        assert result.exit_code == 0
        assert self._validate_no_files_encrypted(tmpdir)
        mock_build.assert_called_once()

    def test_generate_passphrases_using_decrypt_option(self, tmpdir):
        repo_path = self.treasuremap_path
        args = [
            '--decrypt', '-p', tmpdir, '-r', repo_path, 'secrets', 'generate',
            'passphrases', '-s', repo_path, '-a', 'zuul_tester', self.site_name
        ]
        with mock.patch(
                'pegleg.pegleg_main.engine.secrets.generate_passphrases'
        ) as mock_generator:
            result = self.runner.invoke(commands.site, args)
        assert result.exit_code == 0
        assert self._validate_no_files_encrypted(tmpdir)
        mock_generator.assert_called_once()

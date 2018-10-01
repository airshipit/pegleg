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
import pytest

from pegleg import cli
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
class TestSiteCliActions(object):
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

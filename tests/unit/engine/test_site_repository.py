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

import copy
import mock
import os
import yaml

import click
import pytest

from pegleg import config
from pegleg.engine import repository
from pegleg.engine import util

TEST_REPOSITORIES = {
    'repositories': {
        'global': {
            'revision': '843d1a50106e1f17f3f722e2ef1634ae442fe68f',
            'url': 'ssh://REPO_USERNAME@gerrit:29418/aic-clcp-manifests.git'
        },
        'secrets': {
            'revision':
            'master',
            'url': ('ssh://REPO_USERNAME@gerrit:29418/aic-clcp-security-'
                    'manifests.git')
        }
    }
}


@pytest.fixture(autouse=True)
def clean_temp_folders():
    try:
        yield
    finally:
        repository._clean_temp_folders()


@pytest.fixture(autouse=True)
def stub_out_misc_functionality():
    try:
        # Stub out copy functionality.
        mock.patch(
            'pegleg.engine.repository.shutil.copytree', autospec=True).start()
        # Stub out problematic Git functions with these unit tests.
        mock.patch.object(
            util.git,
            'repo_name',
            side_effect=lambda *a, **k: 'test',
            autospec=True).start()
        yield
    finally:
        mock.patch.stopall()


def _repo_name(repo_url):
    repo_name = repo_url.split('/')[-1]
    if repo_name.endswith('.git'):
        return repo_name[:-4]
    return repo_name


def _test_process_repositories_inner(site_name="test_site",
                                     expected_extra_repos=None):
    repository.process_repositories(site_name)
    actual_repo_list = config.get_extra_repo_list()
    expected_repos = expected_extra_repos.get('repositories', {})

    assert len(expected_repos) == len(actual_repo_list)
    for repo in expected_repos.values():
        repo_name = _repo_name(repo['url'])
        assert any(repo_name in r for r in actual_repo_list)


def _test_process_repositories(site_repo=None,
                               repo_username=None,
                               repo_overrides=None):
    """Validate :func:`repository.process_repositories`.

    :param site_repo: Primary site repository.
    :param repo_username: Auth username that replaces REPO_USERNAME.
    :param dict repo_overrides: Overrides with format: -e global=/opt/global,
        keyed with name of override, e.g. global.

    All params above are mutually exclusive. Can only test one at a time.

    """

    @mock.patch.object(
        util.definition,
        'load_as_params',
        autospec=True,
        return_value=TEST_REPOSITORIES)
    @mock.patch.object(
        util.git, 'is_repository', autospec=True, return_value=True)
    @mock.patch.object(
        repository,
        '_handle_repository',
        autospec=True,
        side_effect=lambda repo_url, *a, **k: _repo_name(repo_url))
    def do_test(m_clone_repo, *_):
        _test_process_repositories_inner(
            expected_extra_repos=TEST_REPOSITORIES)

        if site_repo:
            # Validate that the primary site repository is cloned, in addition
            # to the extra repositories.
            repo_revision = None
            repo_url = site_repo.rsplit('@', 1)
            if len(repo_url) == 1:  # Case: local repo path.
                repo_url = repo_url[0]
            elif len(repo_url) == 2:  # Case: remote repo URL.
                repo_url, repo_revision = repo_url
            mock_calls = [
                mock.call(repo_url, ref=repo_revision, auth_key=None)
            ]
            mock_calls.extend([
                mock.call(r['url'], ref=r['revision'], auth_key=None)
                for r in TEST_REPOSITORIES['repositories'].values()
            ])
            m_clone_repo.assert_has_calls(mock_calls)
        elif repo_username:
            # Validate that the REPO_USERNAME placeholder is replaced by
            # repo_username.
            m_clone_repo.assert_has_calls([
                mock.call(
                    r['url'].replace('REPO_USERNAME', repo_username),
                    ref=r['revision'],
                    auth_key=None)
                for r in TEST_REPOSITORIES['repositories'].values()
            ])
        elif repo_overrides:
            # This is computed from: len(cloned extra repos) +
            # len(cloned primary repo), which is len(cloned extra repos) + 1
            expected_call_count = len(TEST_REPOSITORIES['repositories']) + 1
            assert (expected_call_count == m_clone_repo.call_count)

            for x, r in TEST_REPOSITORIES['repositories'].items():
                if x in repo_overrides:
                    ref = None
                    repo_url = repo_overrides[x].rsplit('@', 1)
                    if len(repo_url) == 1:  # Case: local repo path.
                        repo_url = repo_url[0]
                    elif len(repo_url) == 2:  # Case: remote repo URL.
                        repo_url, ref = repo_url
                    repo_url = repo_url.split('=')[-1]
                else:
                    repo_url = r['url']
                    ref = r['revision']
                m_clone_repo.assert_any_call(repo_url, ref=ref, auth_key=None)
        else:
            m_clone_repo.assert_has_calls([
                mock.call(r['url'], ref=r['revision'], auth_key=None)
                for r in TEST_REPOSITORIES['repositories'].values()
            ])

    if site_repo:
        # Set a test site repo, call the test and clean up.
        with mock.patch.object(
                config, 'get_site_repo', autospec=True,
                return_value=site_repo):
            do_test()
    elif repo_username:
        # Set a test repo username, call the test and clean up.
        with mock.patch.object(
                config,
                'get_repo_username',
                autospec=True,
                return_value=repo_username):
            do_test()
    elif repo_overrides:
        with mock.patch.object(
                config,
                'get_extra_repo_overrides',
                autospec=True,
                return_value=list(repo_overrides.values())):
            do_test()
    else:
        do_test()


def test_process_repositories():
    _test_process_repositories()


def test_process_repositories_with_site_repo_url():
    """Test process_repository when site repo is a remote URL."""
    site_repo = (
        'ssh://REPO_USERNAME@gerrit:29418/aic-clcp-site-manifests.git@333')
    _test_process_repositories(site_repo=site_repo)


def test_process_repositories_handles_local_site_repo_path():
    site_repo = '/opt/aic-clcp-site-manifests'
    _test_process_repositories(site_repo=site_repo)


def test_process_repositories_handles_local_site_repo_path_with_revision():
    site_repo = '/opt/aic-clcp-site-manifests@333'
    _test_process_repositories(site_repo=site_repo)


@mock.patch.object(
    util.definition,
    'load_as_params',
    autospec=True,
    return_value=TEST_REPOSITORIES)
@mock.patch('os.path.exists', autospec=True, return_value=True)
@mock.patch.object(
    util.git, 'is_repository', autospec=True, return_value=False)
def test_process_repositories_with_local_site_path_exists_not_repo(*_):
    """Validate that when the site repo already exists but isn't a repository
    that an error is raised.
    """
    with pytest.raises(click.ClickException) as exc:
        _test_process_repositories_inner(
            expected_extra_repos=TEST_REPOSITORIES)
    assert "is not a valid Git repository" in str(exc.value)


def test_process_repositories_with_repo_username():
    _test_process_repositories(repo_username='test_username')


def test_process_repositories_with_repo_overrides_remote_urls():
    # Same URL, different revision (than TEST_REPOSITORIES).
    overrides = {
        'global':
        'global=ssh://REPO_USERNAME@gerrit:29418/aic-clcp-manifests.git@12345'
    }
    _test_process_repositories(repo_overrides=overrides)

    # Different URL, different revision (than TEST_REPOSITORIES).
    overrides = {
        'global': 'global=https://gerrit/aic-clcp-manifests.git@12345'
    }
    _test_process_repositories(repo_overrides=overrides)


def test_process_repositories_with_repo_overrides_local_paths():
    # Local path without revision.
    overrides = {'global': 'global=/opt/aic-clcp-manifests'}
    _test_process_repositories(repo_overrides=overrides)

    # Local path with revision.
    overrides = {'global': 'global=/opt/aic-clcp-manifests@12345'}
    _test_process_repositories(repo_overrides=overrides)


def test_process_repositories_with_multiple_repo_overrides_remote_urls():
    overrides = {
        'global':
        'global=ssh://errit:29418/aic-clcp-manifests.git@12345',
        'secrets':
        'secrets=ssh://gerrit:29418/aic-clcp-security-manifests.git@54321'
    }
    _test_process_repositories(repo_overrides=overrides)


def test_process_repositories_with_multiple_repo_overrides_local_paths():
    overrides = {
        'global': 'global=/opt/aic-clcp-manifests@12345',
        'secrets': 'secrets=/opt/aic-clcp-security-manifests.git@54321'
    }
    _test_process_repositories(repo_overrides=overrides)


@mock.patch.object(
    util.definition,
    'load_as_params',
    autospec=True,
    return_value=TEST_REPOSITORIES)
@mock.patch.object(util.git, 'is_repository', autospec=True, return_value=True)
@mock.patch.object(
    repository,
    '_handle_repository',
    autospec=True,
    side_effect=lambda repo_url, *a, **k: _repo_name(repo_url))
@mock.patch.object(repository, 'LOG', autospec=True)
def test_process_repositiories_extraneous_user_repo_value(m_log, *_):
    repo_overrides = ['global=ssh://gerrit:29418/aic-clcp-manifests.git']

    # Provide a repo user value.
    with mock.patch.object(
            config,
            'get_repo_username',
            autospec=True,
            return_value='test_username'):
        # Get rid of REPO_USERNAME through an override.
        with mock.patch.object(
                config,
                'get_extra_repo_overrides',
                autospec=True,
                return_value=repo_overrides):
            _test_process_repositories_inner(
                expected_extra_repos=TEST_REPOSITORIES)

    msg = ("A repository username was specified but no REPO_USERNAME "
           "string found in repository url %s",
           repo_overrides[0].split('=')[-1])
    m_log.warning.assert_any_call(*msg)


@mock.patch.object(
    util.definition, 'load_as_params', autospec=True,
    return_value={})  # No repositories in site definition.
@mock.patch.object(util.git, 'is_repository', autospec=True, return_value=True)
@mock.patch.object(
    repository,
    '_handle_repository',
    autospec=True,
    side_effect=lambda repo_url, *a, **k: _repo_name(repo_url))
def test_process_repositiories_no_site_def_repos(*_):
    _test_process_repositories_inner(expected_extra_repos={})


@mock.patch.object(
    util.definition, 'load_as_params', autospec=True,
    return_value={})  # No repositories in site definition.
@mock.patch.object(util.git, 'is_repository', autospec=True, return_value=True)
@mock.patch.object(
    repository,
    '_handle_repository',
    autospec=True,
    side_effect=lambda repo_url, *a, **k: _repo_name(repo_url))
@mock.patch.object(repository, 'LOG', autospec=True)
def test_process_repositiories_no_site_def_repos_with_extraneous_overrides(
        m_log, *_):
    """Validate that overrides that don't match site-definition entries are
    ignored.
    """
    site_name = mock.sentinel.site
    repo_overrides = ['global=ssh://gerrit:29418/aic-clcp-manifests.git']
    expected_overrides = {
        'repositories': {
            'global': {
                'revision': '843d1a50106e1f17f3f722e2ef1634ae442fe68f',
                'url': repo_overrides[0]
            }
        }
    }

    # Provide repo overrides.
    with mock.patch.object(
            config,
            'get_extra_repo_overrides',
            autospec=True,
            return_value=repo_overrides):
        _test_process_repositories_inner(
            site_name=site_name, expected_extra_repos=expected_overrides)

    debug_msg = ("Repo override: %s not found under `repositories` for "
                 "site-definition.yaml. Site def repositories: %s",
                 repo_overrides[0], "")
    info_msg = ("No repositories found in site-definition.yaml for site: %s. "
                "Defaulting to specified repository overrides.", site_name)
    m_log.debug.assert_any_call(*debug_msg)
    m_log.info.assert_any_call(*info_msg)


@mock.patch.object(
    util.definition, 'load_as_params', autospec=True,
    return_value={})  # No repositories in site definition.
@mock.patch.object(util.git, 'is_repository', autospec=True, return_value=True)
@mock.patch.object(repository, 'LOG', autospec=True)
def test_process_repositories_without_repositories_key_in_site_definition(
        m_log, *_):
    # Stub this out since default config site repo is '.' and local repo might
    # be dirty.
    with mock.patch.object(
            repository, '_handle_repository', autospec=True, return_value=''):
        _test_process_repositories_inner(
            site_name=mock.sentinel.site, expected_extra_repos={})
    msg = ("The repository for site_name: %s does not contain a "
           "site-definition.yaml with a 'repositories' key" % str(
               mock.sentinel.site))
    assert any(msg in x[1][0] for x in m_log.info.mock_calls)


@mock.patch.object(
    util.definition,
    'load_as_params',
    autospec=True,
    return_value=TEST_REPOSITORIES)
@mock.patch.object(util.git, 'is_repository', autospec=True, return_value=True)
@mock.patch.object(config, 'get_extra_repo_overrides', autospec=True)
def test_process_extra_repositories_malformed_format_raises_exception(
        m_get_extra_repo_overrides, *_):
    # Will fail since it doesn't contain "=".
    broken_repo_url = 'broken_url'
    m_get_extra_repo_overrides.return_value = [broken_repo_url]
    error = ("The repository %s must be in the form of "
             "name=repoUrl[@revision]" % broken_repo_url)

    # Stub this out since default config site repo is '.' and local repo might
    # be dirty.
    with mock.patch.object(
            repository, '_handle_repository', autospec=True, return_value=''):
        with pytest.raises(click.ClickException) as exc:
            repository.process_repositories(mock.sentinel.site)
        assert error == str(exc.value)


@mock.patch.object(util.git, 'is_repository', autospec=True, return_value=True)
def test_process_site_repository(_):
    def _do_test(site_repo):
        expected = site_repo.rsplit('@', 1)[0]

        config.set_site_repo(site_repo)

        with mock.patch.object(
                repository,
                '_handle_repository',
                autospec=True,
                return_value=expected):
            result = repository.process_site_repository()
        assert os.path.normpath(expected) == os.path.normpath(result)

    # Ensure that the reference is always pruned.
    _do_test('http://github.com/openstack/treasuremap@master')
    _do_test('http://github.com/openstack/treasuremap')
    _do_test('https://github.com/openstack/treasuremap@master')
    _do_test('https://github.com/openstack/treasuremap')
    _do_test('ssh://foo@github.com/openstack/treasuremap:12345@master')
    _do_test('ssh://foo@github.com/openstack/treasuremap:12345')

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
import socket
import requests

import fixtures
import mock
import pytest

from pegleg.engine import exceptions
from pegleg.engine.util import git
from tests.unit import test_utils

_REPO_DIR = None
_PROXY_SERVERS = {
    'http':
    os.getenv('HTTP_PROXY',
              os.getenv('http_proxy', 'http://one.proxy.att.com:8888')),
    'https':
    os.getenv('HTTPS_PROXY',
              os.getenv('https_proxy', 'https://one.proxy.att.com:8888'))
}


def is_connected():
    """Verifies whether network connectivity is up.

    :returns: True if connected else False.
    """
    try:
        r = requests.get("http://www.github.com/", proxies={})
        return r.ok
    except requests.exceptions.RequestException:
        return False


def is_connected_behind_proxy():
    """Verifies whether network connectivity is up behind given proxy.

    :returns: True if connected else False.
    """
    try:
        r = requests.get("http://www.github.com/", proxies=_PROXY_SERVERS)
        return r.ok
    except requests.exceptions.RequestException:
        return False


@pytest.fixture()
def clean_git_repo():
    global _REPO_DIR

    try:
        yield
    finally:
        if _REPO_DIR and os.path.exists(_REPO_DIR):
            shutil.rmtree(_REPO_DIR)
            _REPO_DIR = None


def _validate_git_clone(repo_dir, fetched_ref=None, checked_out_ref=None):
    """Validate that git clone/checkout work.

    :param repo_dir: Path to local Git repo.
    :param fetched_ref: Reference that is stored in FETCH_HEAD following a
        remote fetch.
    :param checked_out_ref: Reference that is stored in HEAD following a local
        ref checkout.
    """
    global _REPO_DIR
    _REPO_DIR = repo_dir

    assert os.path.isdir(repo_dir)
    # Assert that the directory is a Git repo.
    assert os.path.isdir(os.path.join(repo_dir, '.git'))
    if fetched_ref:
        # Assert the FETCH_HEAD is at the fetched_ref ref.
        with open(os.path.join(repo_dir, '.git', 'FETCH_HEAD'), 'r') \
                as git_file:
            assert fetched_ref in git_file.read()
    if checked_out_ref:
        # Assert the HEAD is at the checked_out_ref.
        with open(os.path.join(repo_dir, '.git', 'HEAD'), 'r') \
                as git_file:
            assert checked_out_ref in git_file.read()


def _assert_repo_url_was_cloned(mock_log, git_dir):
    expected_msg = ('Treating repo_url=%s as an already-cloned repository')
    assert mock_log.debug.called
    mock_calls = mock_log.debug.mock_calls
    assert any(m[1][0].startswith(expected_msg) for m in mock_calls)
    assert any(m[1][1] == git_dir for m in mock_calls)
    mock_log.debug.reset_mock()


@pytest.mark.skipif(
    not is_connected(), reason='git clone requires network connectivity.')
def test_git_clone_valid_url_http_protocol(clean_git_repo):
    url = 'http://github.com/openstack/airship-armada'
    git_dir = git.git_handler(url, ref='master')
    _validate_git_clone(git_dir)


@pytest.mark.skipif(
    not is_connected(), reason='git clone requires network connectivity.')
def test_git_clone_valid_url_https_protocol(clean_git_repo):
    url = 'https://github.com/openstack/airship-armada'
    git_dir = git.git_handler(url, ref='master')
    _validate_git_clone(git_dir)


@pytest.mark.skipif(
    not is_connected(), reason='git clone requires network connectivity.')
def test_git_clone_with_commit_reference(clean_git_repo):
    url = 'https://github.com/openstack/airship-armada'
    commit = 'cba78d1d03e4910f6ab1691bae633c5bddce893d'
    git_dir = git.git_handler(url, commit)
    _validate_git_clone(git_dir, commit)


@pytest.mark.skipif(
    not is_connected(), reason='git clone requires network connectivity.')
def test_git_clone_with_patch_ref(clean_git_repo):
    ref = 'refs/changes/54/457754/73'
    git_dir = git.git_handler('https://github.com/openstack/openstack-helm',
                              ref)
    _validate_git_clone(git_dir, ref)


@pytest.mark.skipif(
    not is_connected_behind_proxy(),
    reason='git clone requires proxy connectivity.')
@mock.patch.object(git, 'LOG', autospec=True)
def test_git_clone_behind_proxy(mock_log, clean_git_repo):
    url = 'https://github.com/openstack/airship-armada'
    commit = 'cba78d1d03e4910f6ab1691bae633c5bddce893d'

    for proxy_server in _PROXY_SERVERS.values():
        git_dir = git.git_handler(url, commit, proxy_server=proxy_server)
        _validate_git_clone(git_dir, commit)

        mock_log.debug.assert_any_call('Cloning [%s] with proxy [%s]', url,
                                       proxy_server)
        mock_log.debug.reset_mock()


@pytest.mark.skipif(
    not is_connected(), reason='git clone requires network connectivity.')
@mock.patch.object(git, 'LOG', autospec=True)
def test_git_clone_existing_directory_checks_out_earlier_ref_from_local(
        mock_log, clean_git_repo):
    """Validate Git checks out an earlier patch or ref that should exist
    locally (as a later ref was already fetched which should contain that
    revision history).
    """
    # Clone the openstack-helm repo and automatically checkout patch 34.
    ref = 'refs/changes/15/536215/35'
    repo_url = 'https://github.com/openstack/openstack-helm'
    git_dir = git.git_handler(repo_url, ref)
    _validate_git_clone(git_dir, fetched_ref=ref)

    # Checkout ref='master' now that the repo already exists locally.
    ref = 'refs/changes/15/536215/34'
    git_dir = git.git_handler(git_dir, ref)
    _validate_git_clone(git_dir, checked_out_ref=ref)
    _assert_repo_url_was_cloned(mock_log, git_dir)


@pytest.mark.skipif(
    not is_connected(), reason='git clone requires network connectivity.')
@mock.patch.object(git, 'LOG', autospec=True)
def test_git_clone_existing_directory_checks_out_master_from_local(
        mock_log, clean_git_repo):
    """Validate Git checks out the ref of an already cloned repo that exists
    locally.
    """
    # Clone the openstack-helm repo and automatically checkout patch 34.
    ref = 'refs/changes/15/536215/34'
    repo_url = 'https://github.com/openstack/openstack-helm'
    git_dir = git.git_handler(repo_url, ref)
    _validate_git_clone(git_dir, fetched_ref=ref)

    # Checkout ref='master' now that the repo already exists locally.
    ref = 'master'
    git_dir = git.git_handler(git_dir, ref)
    _validate_git_clone(git_dir, checked_out_ref=ref)
    _assert_repo_url_was_cloned(mock_log, git_dir)


@pytest.mark.skipif(
    not is_connected(), reason='git clone requires network connectivity.')
@mock.patch.object(git, 'LOG', autospec=True)
def test_git_clone_checkout_refpath_saves_references_locally(
        mock_log, clean_git_repo):
    """Validate that refpath/hexsha branches are created in the local repo
    following clone of the repo using a refpath during initial checkout.
    """
    # Clone the openstack-helm repo and automatically checkout patch 34.
    ref = 'refs/changes/15/536215/34'
    repo_url = 'https://github.com/openstack/openstack-helm'
    git_dir = git.git_handler(repo_url, ref)
    _validate_git_clone(git_dir, fetched_ref=ref)

    # Now checkout patch 34 again to ensure it's still there.
    ref = 'refs/changes/15/536215/34'
    git_dir = git.git_handler(git_dir, ref)
    _validate_git_clone(git_dir, checked_out_ref=ref)
    _assert_repo_url_was_cloned(mock_log, git_dir)

    # Verify that passing in the hexsha variation of refpath
    # 'refs/changes/15/536215/34' also works.
    hexref = '276102a115dac3c0a6e91f9047d8b086bc8d2ff0'
    git_dir = git.git_handler(git_dir, hexref)
    _validate_git_clone(git_dir, checked_out_ref=hexref)
    _assert_repo_url_was_cloned(mock_log, git_dir)


@pytest.mark.skipif(
    not is_connected(), reason='git clone requires network connectivity.')
@mock.patch.object(git, 'LOG', autospec=True)
def test_git_clone_checkout_hexsha_saves_references_locally(
        mock_log, clean_git_repo):
    """Validate that refpath/hexsha branches are created in the local repo
    following clone of the repo using a hexsha during initial checkout.
    """
    # Clone the openstack-helm repo and automatically checkout patch using
    # hexsha.
    # NOTE(felipemonteiro): We have to use the commit ID (hexsha) corresponding
    # to the last patch as that is what gets pushed to github. In this case,
    # this corresponds to patch 'refs/changes/15/536215/35'.
    ref = 'bf126f46b1c175a8038949a87dafb0a716e3b9b6'
    repo_url = 'https://github.com/openstack/openstack-helm'
    git_dir = git.git_handler(repo_url, ref)
    _validate_git_clone(git_dir, fetched_ref=ref)

    # Now checkout patch using hexsha again to ensure it's still there.
    ref = 'bf126f46b1c175a8038949a87dafb0a716e3b9b6'
    git_dir = git.git_handler(git_dir, ref)
    _validate_git_clone(git_dir, checked_out_ref=ref)
    _assert_repo_url_was_cloned(mock_log, git_dir)

    # Verify that passing in the refpath variation of hexsha also works.
    hexref = 'refs/changes/15/536215/35'
    git_dir = git.git_handler(git_dir, hexref)
    _validate_git_clone(git_dir, checked_out_ref=hexref)
    _assert_repo_url_was_cloned(mock_log, git_dir)


@pytest.mark.skipif(
    not is_connected(), reason='git clone requires network connectivity.')
@mock.patch.object(git, 'LOG', autospec=True)
def test_git_clone_existing_directory_checks_out_next_local_ref(
        mock_log, clean_git_repo):
    """Validate Git fetches the newer ref upstream that doesn't exist locally
    in the cloned repo.
    """
    # Clone the openstack-helm repo and automatically checkout patch 73.
    ref = 'refs/changes/54/457754/73'
    repo_url = 'https://github.com/openstack/openstack-helm'
    git_dir = git.git_handler(repo_url, ref)
    _validate_git_clone(git_dir, ref)

    # Attempt to checkout patch 74 which requires a remote fetch even though
    # the repo has already been cloned.
    ref = 'refs/changes/54/457754/74'
    git_dir = git.git_handler(git_dir, ref)
    _validate_git_clone(git_dir, ref)
    _assert_repo_url_was_cloned(mock_log, git_dir)


@pytest.mark.skipif(
    not is_connected(), reason='git clone requires network connectivity.')
@mock.patch.object(git, 'LOG', autospec=True)
def test_git_clone_delete_repo_and_reclone(mock_log, clean_git_repo):
    """Validate that cloning a repo, then deleting it, then recloning it works.
    """
    # Clone the openstack-helm repo and automatically checkout patch 73.
    ref = 'refs/changes/54/457754/73'
    repo_url = 'https://github.com/openstack/openstack-helm'
    first_git_dir = git.git_handler(repo_url, ref)
    _validate_git_clone(first_git_dir, ref)

    # Validate that the repo was cloned.
    assert mock_log.debug.called
    mock_log.debug.assert_any_call('Cloning [%s]', repo_url)
    mock_log.debug.reset_mock()

    # Delete the just-cloned repo.
    shutil.rmtree(first_git_dir)

    # Verify that checking out the same ref results in a re-clone.
    second_git_dir = git.git_handler(repo_url, ref)
    _validate_git_clone(second_git_dir, ref)

    # Validate that the repo was cloned.
    assert first_git_dir != second_git_dir
    assert mock_log.debug.called
    mock_log.debug.assert_any_call('Cloning [%s]', repo_url)


@pytest.mark.skipif(
    not is_connected(), reason='git clone requires network connectivity.')
@mock.patch.object(git, 'LOG', autospec=True)
def test_git_clone_clean_dirty_local_repo(mock_log, clean_git_repo):
    """Validate that a dirty repo is cleaned before a ref is checked out."""
    ref = 'refs/changes/54/457754/73'
    repo_url = 'https://github.com/openstack/openstack-helm'
    git_dir = git.git_handler(repo_url, ref)
    _validate_git_clone(git_dir, ref)

    file_to_rename = os.path.join(git_dir, os.listdir(git_dir)[0])
    os.rename(file_to_rename, file_to_rename + '-renamed')

    git_dir = git.git_handler(git_dir, ref)
    _validate_git_clone(git_dir, ref)

    assert mock_log.warning.called
    mock_log.warning.assert_any_call(
        'The locally cloned repo_url=%s is dirty. Cleaning up untracked '
        'files.', git_dir)


@pytest.mark.skipif(
    not is_connected(), reason='git clone requires network connectivity.')
@mock.patch.object(git, 'LOG', autospec=True)
def test_git_clone_existing_directory_raises_exc_for_invalid_ref(
        mock_log, clean_git_repo):
    """Validate Git throws an error for an invalid ref when trying to checkout
    a ref for an already-cloned repo.
    """
    # Clone the openstack-helm repo and automatically checkout patch 73.
    ref = 'refs/changes/54/457754/73'
    repo_url = 'https://github.com/openstack/openstack-helm'
    git_dir = git.git_handler(repo_url, ref)
    _validate_git_clone(git_dir, ref)

    # Attempt to checkout patch 9000 now that the repo already exists locally.
    ref = 'refs/changes/54/457754/9000'
    with pytest.raises(exceptions.GitException):
        git_dir = git.git_handler(git_dir, ref)
    _assert_repo_url_was_cloned(mock_log, git_dir)


@pytest.mark.skipif(
    not is_connected(), reason='git clone requires network connectivity.')
def test_git_clone_empty_url_raises_value_error(clean_git_repo):
    url = ''
    with pytest.raises(ValueError):
        git.git_handler(url, ref='master')


@pytest.mark.skipif(
    not is_connected(), reason='git clone requires network connectivity.')
def test_git_clone_invalid_url_type_raises_value_error(clean_git_repo):
    url = 5
    with pytest.raises(ValueError):
        git.git_handler(url, ref='master')


@pytest.mark.skipif(
    not is_connected(), reason='git clone requires network connectivity.')
def test_git_clone_invalid_local_repo_url_raises_notadirectory_error(
        clean_git_repo):
    url = False
    with pytest.raises(NotADirectoryError):
        git.git_handler(url, ref='master')


@pytest.mark.skipif(
    not is_connected(), reason='git clone requires network connectivity.')
def test_git_clone_invalid_remote_url(clean_git_repo):
    url = 'https://github.com/dummy/armada'
    with pytest.raises(exceptions.GitException):
        git.git_handler(url, ref='master')


@pytest.mark.skipif(
    not is_connected(), reason='git clone requires network connectivity.')
def test_git_clone_invalid_remote_url_protocol(clean_git_repo):
    url = 'ftp://foo.bar'
    with pytest.raises(ValueError):
        git.git_handler(url, ref='master')


@pytest.mark.skipif(
    not is_connected(), reason='git clone requires network connectivity.')
def test_git_clone_fake_proxy(clean_git_repo):
    url = 'https://github.com/openstack/airship-armada'
    proxy_url = test_utils.rand_name(
        'not.a.proxy.that.works.and.never.will', prefix='http://') + ":8080"

    with pytest.raises(exceptions.GitProxyException):
        git.git_handler(url, ref='master', proxy_server=proxy_url)


@pytest.mark.skipif(
    not is_connected(), reason='git clone requires network connectivity.')
@mock.patch('os.path.exists', return_value=True, autospec=True)
def test_git_clone_ssh_auth_method_fails_auth(_, clean_git_repo):
    fake_user = test_utils.rand_name('fake_user')
    url = ('ssh://%s@review.openstack.org:29418/openstack/airship-armada' %
           fake_user)
    with pytest.raises(exceptions.GitAuthException):
        git._try_git_clone(
            url, ref='refs/changes/17/388517/5', auth_key='/home/user/.ssh/')


@pytest.mark.skipif(
    not is_connected(), reason='git clone requires network connectivity.')
@mock.patch('os.path.exists', return_value=False, autospec=True)
def test_git_clone_ssh_auth_method_missing_ssh_key(_, clean_git_repo):
    fake_user = test_utils.rand_name('fake_user')
    url = ('ssh://%s@review.openstack.org:29418/openstack/airship-armada' %
           fake_user)
    with pytest.raises(exceptions.GitSSHException):
        git.git_handler(
            url, ref='refs/changes/17/388517/5', auth_key='/home/user/.ssh/')

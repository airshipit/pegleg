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

import logging
import os
import tempfile
from urllib.parse import urlparse

import click
from git import exc as git_exc
from git import Git
from git import Repo

from pegleg.engine import exceptions

LOG = logging.getLogger(__name__)

__all__ = ('git_handler', )


def git_handler(repo_url, ref=None, proxy_server=None, auth_key=None):
    """Handle directories that are Git repositories.

    If ``repo_url`` is a valid URL for which a local repository doesn't
    exist, then clone ``repo_url`` and checkout the given ``ref``. Otherwise,
    treat ``repo_url`` as an already-cloned repository and checkout the given
    ``ref``.

    Supported ``ref`` formats include:

    * branch name (e.g. 'master')
    * refpath (e.g. 'refs/changes/54/457754/73')
    * hexsha (e.g. 'ff5496b9c781918fdc49d79f927323eeef2f5320')

    :param repo_url: URL of remote Git repo or path to local Git repo. If no
        local copy exists, clone it. Afterward, check out ``ref`` in the repo.
    :param ref: branch, commit or reference in the repo to clone. None causes
        the currently checked out reference to be used (if repo exists).
    :param proxy_server: optional, HTTP proxy to use while cloning the repo.
    :param auth_key: If supplied results in using SSH to clone the repository
        with the specified key.  If the value is None, SSH is not used.
    :returns: Path to the cloned repo if a repo was cloned, else absolute
        path to ``repo_url``.
    :raises ValueError: If ``repo_url`` isn't a valid URL or doesn't begin
        with a valid protocol (http, https or ssh) for cloning.
    :raises NotADirectoryError: If ``repo_url`` isn't a valid directory path.

    """

    supported_clone_protocols = ('http', 'https', 'ssh')

    try:
        parsed_url = urlparse(repo_url)
    except Exception as e:
        raise ValueError('repo_url=%s is invalid. Details: %s' % (repo_url, e))

    if ref is None:
        ref = _get_current_ref(repo_url)

    if not os.path.exists(repo_url):
        # we need to clone the repo_url first since it doesn't exist and then
        # checkout the appropriate reference - and return the tmpdir
        if parsed_url.scheme in supported_clone_protocols:
            return _try_git_clone(repo_url, ref, proxy_server, auth_key)
        else:
            raise ValueError('repo_url=%s must use one of the following '
                             'protocols: %s' %
                             (repo_url, ', '.join(supported_clone_protocols)))
    # otherwise, we're dealing with a local directory so although
    # we do not need to clone, we may need to process the reference
    # by checking that out and returning the directory they passed in
    else:
        LOG.debug('Treating repo_url=%s as an already-cloned repository. '
                  'Attempting to checkout ref=%s', repo_url, ref)
        try:
            # get absolute path of what is probably a directory
            repo_url, _ = normalize_repo_path(repo_url)
        except Exception:
            msg = "The repo_url=%s is not a valid Git repo" % repo_url
            LOG.error(msg)
            raise NotADirectoryError(msg)

        repo = Repo(repo_url, search_parent_directories=True)
        if repo.is_dirty(untracked_files=True):
            # NOTE(felipemonteiro): This code should never be executed on a
            # real local repository. Wrapper logic around this module will
            # only perform this functionality against a temporary replica of
            # local repositories, making the below operations safe.
            LOG.info('Replica of local repo=%s is dirty. Committing all '
                     'tracked/untracked changes to ref=%s',
                     repo_name(repo_url), ref)
            repo.git.add(all=True)
            repo.index.commit('Temporary Pegleg commit')

        try:
            # Check whether the ref exists locally.
            LOG.info('Attempting to checkout ref=%s from repo_url=%s locally',
                     ref, repo_url)
            _try_git_checkout(repo, repo_url, ref, fetch=False)
        except exceptions.GitException:
            # Otherwise, attempt to fetch and checkout the missing ref.
            LOG.info('ref=%s not found locally for repo_url=%s, fetching from '
                     'remote', ref, repo_url)
            # Allow any errors to bubble up.
            _try_git_checkout(repo, repo_url, ref, fetch=True)

        return repo_url


def _get_current_ref(repo_url):
    """If no ``ref`` is provided, then the most logical assumption is that
    the current revision in the checked out repo should be used. If the
    repo hasn't been cloned yet, None will be returned, in which case GitPython
    will use the repo's config's fetch refspec instead.

    :param repo_url: URL of remote Git repo or path to local Git repo.

    """

    try:
        repo = Repo(repo_url, search_parent_directories=True)
        current_ref = repo.head.ref.name
        LOG.debug('ref for repo_url=%s not specified, defaulting to currently '
                  'checked out ref=%s', repo_url, current_ref)
        return current_ref
    except Exception as e:
        return None


def _try_git_clone(repo_url, ref=None, proxy_server=None, auth_key=None):
    """Try cloning Git repo from ``repo_url`` using the reference ``ref``.

    :param repo_url: URL of remote Git repo or path to local Git repo.
    :param ref: branch, commit or reference in the repo to clone.
    :param proxy_server: optional, HTTP proxy to use while cloning the repo.
    :param auth_key: If supplied results in using SSH to clone the repository
        with the specified key.  If the value is None, SSH is not used.
    :returns: Path to the cloned repo.
    :rtype: str
    :raises GitException: If ``repo_url`` is invalid or could not be found.
    :raises GitAuthException: If authentication with the Git repository failed.
    :raises GitProxyException: If the repo could not be cloned due to a proxy
        issue.

    """

    # the name here is important as it bubbles back up to the output filename
    # and ensure we handle url/foo.git/ cases. prefix is 'tmp' by default.
    root_temp_dir = tempfile.mkdtemp()
    repo_name = repo_url.rstrip('/').split('/')[-1]
    temp_dir = os.path.join(root_temp_dir, repo_name)
    os.makedirs(temp_dir)

    env_vars = _get_clone_env_vars(repo_url, ref, auth_key)
    ssh_cmd = env_vars.get('GIT_SSH_COMMAND')

    try:
        if proxy_server:
            LOG.debug('Cloning [%s] with proxy [%s]', repo_url, proxy_server)
            # TODO(felipemonteiro): proxy_server can be finicky. Need a config
            # option to retry up to N times.
            repo = Repo.clone_from(
                repo_url,
                temp_dir,
                config='http.proxy=%s' % proxy_server,
                env=env_vars)
        else:
            LOG.debug('Cloning [%s]', repo_url)
            repo = Repo.clone_from(repo_url, temp_dir, env=env_vars)
    except git_exc.GitCommandError as e:
        LOG.exception('Failed to clone repo_url=%s using ref=%s.', repo_url,
                      ref)
        if (ssh_cmd and ssh_cmd in e.stderr
                or 'permission denied' in e.stderr.lower()):
            raise exceptions.GitAuthException(repo_url, auth_key)
        elif 'could not resolve proxy' in e.stderr.lower():
            raise exceptions.GitProxyException(proxy_server)
        else:
            raise exceptions.GitException(repo_url, details=e)
    except Exception as e:
        msg = 'Encountered unknown Exception during clone of %s' % repo_url
        LOG.exception(msg)
        raise exceptions.GitException(repo_url, details=e)

    _try_git_checkout(repo=repo, repo_url=repo_url, ref=ref)

    return temp_dir


def _get_clone_env_vars(repo_url, ref, auth_key):
    """Generate environment variables include SSH command for Git clone.

    :param repo_url: URL of remote Git repo or path to local Git repo.
    :param ref: branch, commit or reference in the repo to clone.
    :param auth_key: If supplied results in using SSH to clone the repository
        with the specified key.  If the value is None, SSH is not used.
    :returns: Dictionary of key-value pairs for Git clone.
    :rtype: dict
    :raises GitSSHException: If the SSH key specified by ``CONF.ssh_key_path``
        could not be found and ``auth_method`` is "SSH".

    """
    ssh_cmd = None
    env_vars = {'GIT_TERMINAL_PROMPT': '0'}

    if auth_key:
        if os.path.exists(auth_key):
            LOG.debug('Attempting to clone the repo at %s using reference %s '
                      'with SSH authentication.', repo_url, ref)
            # Ensure that host checking is ignored, to avoid unnecessary
            # required CLI input.
            ssh_cmd = (
                'ssh -i {} -o ConnectionAttempts=20 -o ConnectTimeout=10 -o '
                'StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null'
                .format(os.path.expanduser(auth_key)))
            env_vars.update({'GIT_SSH_COMMAND': ssh_cmd})
        else:
            msg = "The auth_key path '%s' was not found" % auth_key
            LOG.error(msg)
            raise exceptions.GitSSHException(auth_key)
    return env_vars


def _try_git_checkout(repo, repo_url, ref=None, fetch=True):
    """Try to checkout a ``ref`` from ``repo``.

    Local branches are created for multiple variations of the ``ref``,
    including its refpath and hexpath (i.e. commit ID).

    This is to locally "cache" references that would otherwise require
    resolution upstream. We increase performance by creating local branches
    for these other ``ref`` formats when the ``ref`` is fetched remotely for
    the first time only.

    :param repo: Git Repo object.
    :param repo_url: URL of remote Git repo or path to local Git repo.
    :param ref: branch, commit or reference in the repo to clone.
    :param fetch: Whether to fetch the ``ref`` from remote before checkout or
        to use the already-cloned local repo.
    :raises GitException: If ``ref`` could not be checked out.

    """
    try:
        g = Git(repo.working_dir)
        branches = [b.name for b in repo.branches]
        LOG.debug('Available branches for repo_url=%s: %s', repo_url, branches)

        if fetch:
            LOG.debug('Fetching ref=%s from remote repo_url=%s', ref, repo_url)
            # fetch_info is guaranteed to be populated if ref resolves, else
            # a GitCommandError is raised.
            fetch_info = repo.remotes.origin.fetch(ref)
            hexsha = fetch_info[0].commit.hexsha.strip()
            ref_path = fetch_info[0].remote_ref_path.strip()

            # If ``ref`` doesn't match the hexsha/refpath then create a branch
            # for each so that future checkouts can be performed using either
            # format. This way, no future processing is required to figure
            # out whether a refpath/hexsha exists within the repo.
            _create_local_ref(
                g, branches, ref=ref, newref=hexsha, reftype='hexsha')
            _create_local_ref(
                g, branches, ref=ref, newref=ref_path, reftype='refpath')
            _create_or_checkout_local_ref(g, branches, ref=ref)
        else:
            LOG.debug('Checking out ref=%s from local repo_url=%s', ref,
                      repo_url)
            # Expect the reference to exist if checking out locally.
            g.checkout(ref)

        LOG.debug('Successfully checked out ref=%s for repo_url=%s', ref,
                  repo_url)
    except git_exc.GitCommandError as e:
        LOG.exception('Failed to checkout ref=%s from repo_url=%s.', ref,
                      repo_url)
        raise exceptions.GitException(repo_url, details=e)
    except Exception as e:
        msg = ('Encountered unknown Exception during checkout of ref=%s for '
               'repo_url=%s' % (ref, repo_url))
        LOG.exception(msg)
        raise exceptions.GitException(repo_url, details=e)


def _create_or_checkout_local_ref(g, branches, ref):
    if ref not in branches:
        LOG.debug('Creating local branch for ref=%s', ref)
        g.checkout('FETCH_HEAD', b=ref)
        branches.append(ref)
    else:
        LOG.debug('Checking out ref=%s from local repo', ref)
        g.checkout('FETCH_HEAD')


def _create_local_ref(g, branches, ref, newref, reftype=None):
    if newref not in branches:
        if newref and ref != newref:
            LOG.debug('Creating local branch for ref=%s (%s for %s)', newref,
                      reftype, ref)
            g.checkout('FETCH_HEAD', b=newref)
            branches.append(newref)


def is_repository(path, *args, **kwargs):
    """Checks whether the directory ``path`` is a Git repository.

    :param str path: Directory path to check.
    :returns: True if ``path`` is a repo, else False.
    :rtype: boolean

    """

    try:
        Repo(path, *args, **kwargs).git_dir
        return True
    except git_exc.InvalidGitRepositoryError:
        return False


def is_equal(first_repo, other_repo):
    """Compares whether two repositories are the same.

    Sameness is defined as whether they point to the same remote repository.

    :param str first_repo: Path or URL of first repository.
    :param str other_repo: Path or URL of other repository.
    :returns: True if both are the same, else False.
    :rtype: boolean

    """

    if not is_repository(first_repo) or not is_repository(other_repo):
        return False

    try:
        # Compare whether the first reference from each repository is the
        # same: by doing so we know the repositories are the same.
        first = Repo(first_repo, search_parent_directories=True)
        other = Repo(other_repo, search_parent_directories=True)
        first_rev = first.git.rev_list('master').splitlines()[-1]
        other_rev = other.git.rev_list('master').splitlines()[-1]
        return first_rev == other_rev
    except Exception:
        return False


def repo_name(repo_url_or_path):
    """Get the repository name for the local or remote repo at
    ``repo_url_or_path``.

    :param repo_url: URL of remote Git repo or path to local Git repo.
    :returns: Corresponding repo name.
    :rtype: str
    :raises GitConfigException: If the path is not a valid Git repo.

    """

    if not is_repository(repo_url_or_path):
        raise exceptions.GitConfigException(repo_url=repo_url_or_path)

    repo = Repo(repo_url_or_path, search_parent_directories=True)
    config_reader = repo.config_reader()
    section = 'remote "origin"'
    option = 'url'

    if config_reader.has_section(section):
        repo_url = config_reader.get_value(section, option)
        try:
            # Support repos that end with or without '.git'
            if repo_url.endswith('.git'):
                return repo_url.split('/')[-1].split('.git')[0]
            else:
                if repo_url.endswith('/'):
                    return repo_url.split('/')[-2]
                else:
                    return repo_url.split('/')[-1]
        except Exception:
            raise exceptions.GitConfigException(repo_url=repo_url_or_path)

    raise exceptions.GitConfigException(repo_url=repo_url_or_path)


def normalize_repo_path(repo_path):
    """A utility function for retrieving the root repo path when the site
    repository path contains subfolders.

    Given (for example): ../airship-in-a-bottle/deployment_files@master

    It is necessary to pass ../airship-in-a-bottle to Git for checkout/clone
    as that is the actual repository path.

    Yet it is necessary to pass ../airship-in-a-bottle/deployment_files to
    :func:`util.definition.site_files_by_repo` for discovering the
    site-definition.yaml.

    """

    orig_repo_path = repo_path
    sub_path = ""

    # Only resolve the root path if it's not a URL and exists.
    if os.path.exists(repo_path):
        repo_path = os.path.abspath(repo_path)
        while (repo_path and os.path.exists(repo_path)
               and not is_repository(repo_path)):
            paths = repo_path.rsplit("/", 1)
            if not all(paths):
                break
            repo_path = os.path.abspath(paths[0])
            sub_path = os.path.join(sub_path, paths[1])
        if not repo_path or not is_repository(repo_path):
            raise click.ClickException(
                "Specified site repo path=%s exists but isn't a Git "
                "repository" % orig_repo_path)

    return repo_path, sub_path

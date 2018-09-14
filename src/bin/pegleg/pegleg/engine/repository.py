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

import atexit
import logging
import os
import shutil
import tempfile

import click

from pegleg import config
from pegleg.engine import exceptions
from pegleg.engine import util

__all__ = ('process_repositories', 'process_site_repository')

__REPO_FOLDERS = {}
_INVALID_FORMAT_MSG = ("The repository %s must be in the form of "
                       "name=repoUrl[@revision]")

LOG = logging.getLogger(__name__)


@atexit.register
def _clean_temp_folders():
    global __REPO_FOLDERS

    for r in __REPO_FOLDERS.values():
        shutil.rmtree(r, ignore_errors=True)


def process_repositories(site_name):
    """Process and setup all repositories including ensuring we are at the
    right revision based on the site's own site-definition.yaml file.

    :param site_name: Site name for which to clone relevant repos.

    """

    # Only tracks extra repositories - not the site (primary) repository.
    extra_repos = []

    site_repo = process_site_repository()

    # Retrieve extra repo data from site-definition.yaml files.
    site_data = util.definition.load_as_params(
        site_name, primary_repo_base=site_repo)
    site_def_repos = _get_and_validate_site_repositories(site_name, site_data)

    # Dict mapping repository names to associated URL/revision info for clone.
    repo_overrides = _process_repository_overrides(site_def_repos)
    if not site_def_repos:
        LOG.info('No repositories found in site-definition.yaml for site: %s. '
                 'Defaulting to specified repository overrides.', site_name)
        site_def_repos = repo_overrides

    # Extract user/key that we will use for all repositories.
    repo_key = config.get_repo_key()
    repo_user = config.get_repo_username()

    for repo_alias in site_def_repos.keys():
        if repo_alias == "site":
            LOG.warning("The primary site repository path must be specified "
                        "via the -r flag. Ignoring the provided "
                        "site-definition entry: %s",
                        site_def_repos[repo_alias])
            continue

        # Extract URL and revision, prioritizing overrides over the defaults in
        # the site-definition.yaml.
        if repo_alias in repo_overrides:
            repo_path_or_url = repo_overrides[repo_alias]['url']
            repo_revision = repo_overrides[repo_alias]['revision']
        else:
            repo_path_or_url = site_def_repos[repo_alias]['url']
            repo_revision = site_def_repos[repo_alias]['revision']

        # If a repo user is provided, do the necessary replacements.
        if repo_user:
            if "REPO_USERNAME" not in repo_path_or_url:
                LOG.warning(
                    "A repository username was specified but no REPO_USERNAME "
                    "string found in repository url %s", repo_path_or_url)
            else:
                repo_path_or_url = repo_path_or_url.replace(
                    'REPO_USERNAME', repo_user)

        LOG.info("Processing repository %s with url=%s, repo_key=%s, "
                 "repo_username=%s, revision=%s", repo_alias, repo_path_or_url,
                 repo_key, repo_user, repo_revision)

        temp_extra_repo = _copy_to_temp_folder(repo_path_or_url, repo_alias)
        temp_extra_repo = _handle_repository(
            temp_extra_repo, ref=repo_revision, auth_key=repo_key)
        extra_repos.append(temp_extra_repo)

    # Overwrite the site repo and extra repos in the config because further
    # processing will fail if they contain revision info in their paths.
    LOG.debug("Updating site_repo=%s extra_repo_list=%s in config", site_repo,
              extra_repos)
    config.set_site_repo(site_repo)
    config.set_extra_repo_list(extra_repos)


def process_site_repository(update_config=False):
    """Process and setup site repository including ensuring we are at the right
    revision based on the site's own site-definition.yaml file.

    :param bool update_config: Whether to update Pegleg config with computed
        site repo path.

    """

    # Retrieve the main site repository and validate it.
    site_repo_or_path = config.get_site_repo()
    if not site_repo_or_path:
        raise ValueError("Site repository directory (%s) must be specified" %
                         site_repo_or_path)

    repo_path_or_url, repo_revision = _extract_repo_url_and_revision(
        site_repo_or_path)
    temp_site_repo = _copy_to_temp_folder(repo_path_or_url, "site")
    _process_site_repository(temp_site_repo, repo_revision)

    if update_config:
        # Overwrite the site repo in the config because further processing will
        # fail if they contain revision info in their paths.
        LOG.debug("Updating site_repo=%s in config", temp_site_repo)
        config.set_site_repo(temp_site_repo)

    return temp_site_repo


def _process_site_repository(repo_url_or_path, repo_revision):
    """Process the primary or site repository located at ``repo_url_or_path``.

    Also validate that the provided ``repo_url_or_path`` is a valid Git
    repository. If ``repo_url_or_path`` doesn't already exist, clone it.
    If it does, extra the appropriate revision and check it out.

    :param repo_url_or_path: Repo URL and associated auth information. E.g.:

        * ssh://REPO_USERNAME@<GERRIT_URL>:29418/aic-clcp-manifests.git@<ref>
        * https://<GERRIT_URL>/aic-clcp-manifests.git@<ref>
        * http://<GERRIT_URL>/aic-clcp-manifests.git@<ref>
        * <LOCAL_REPO_PATH>@<ref>
        * same values as above without @<ref>

    """

    repo_alias = 'site'  # We are processing the site repo necessarily.
    repo_key = config.get_repo_key()
    repo_user = config.get_repo_username()

    LOG.info("Processing repository %s with url=%s, repo_key=%s, "
             "repo_username=%s, revision=%s", repo_alias, repo_url_or_path,
             repo_key, repo_user, repo_revision)
    _handle_repository(repo_url_or_path, ref=repo_revision, auth_key=repo_key)


def _get_and_validate_site_repositories(site_name, site_data):
    """Validate that repositories entry exists in ``site_data``."""
    if 'repositories' not in site_data:
        LOG.info("The repository for site_name: %s does not contain a "
                 "site-definition.yaml with a 'repositories' key. Ensure "
                 "your repository is self-contained and doesn't require "
                 "extra repositories for correct rendering." % site_name)
    return site_data.get('repositories', {})


def _copy_to_temp_folder(repo_path_or_url, repo_alias):
    """Helper to ensure that local repos remain untouched by Pegleg processing.
    This is accomplished by copying local repos into temp folders.

    """

    global __REPO_FOLDERS

    if os.path.exists(repo_path_or_url):
        repo_name = util.git.repo_name(repo_path_or_url)
        new_temp_path = os.path.join(tempfile.mkdtemp(), repo_name)
        norm_path, sub_path = util.git.normalize_repo_path(repo_path_or_url)
        shutil.copytree(src=norm_path, dst=new_temp_path, symlinks=True)
        __REPO_FOLDERS.setdefault(repo_name, new_temp_path)
        return os.path.join(new_temp_path, sub_path)
    else:
        return repo_path_or_url


def _process_repository_overrides(site_def_repos):
    """Process specified repository overrides via the CLI ``-e`` flag.

    This will resolve ``-e`` site CLI arguments and override the corresponding
    values in the relevant :file:`site-definition.yaml`, if applicable.

    For example, given CLI override of::

        -e global=/opt/global@foo

    And site-definition.yaml ``repositories`` value of::

        repositories:
          global:
            revision: bar
            url: /opt/global

    Then the resulting dictionary that is returned will be::

        {"global": {"url": "/opt/global", "revision": "foo"}}

    :param site_def_repos: Dictionary of ``repositories`` field included
        in relevant :file:`site-definition.yaml`.
    :returns: Dictionary with above format.

    """

    # Extra repositories to process.
    provided_repo_overrides = config.get_extra_repo_store()
    # Map repository names to the associated URL/revision for cloning.
    repo_overrides = {}

    for repo_override in provided_repo_overrides:
        # break apart global=repoUrl
        try:
            repo_alias, repo_url_or_path = repo_override.split('=', 1)
        except ValueError:
            # TODO(felipemonteiro): Use internal exceptions for this.
            raise click.ClickException(_INVALID_FORMAT_MSG % repo_override)

        if repo_alias == "site":
            LOG.warning("The primary site repository path must be specified "
                        "via the -r flag. Ignoring the provided override: %s",
                        repo_override)
            continue

        if repo_alias not in site_def_repos:
            # If we are overriding a value that doesn't exist in the
            # site-definition.yaml make a note of it in case the override
            # is something bogus, but we won't make this a hard requirement,
            # so just log the discrepancy.
            LOG.debug("Repo override: %s not found under `repositories` for "
                      "site-definition.yaml. Site def repositories: %s",
                      repo_override, ", ".join(site_def_repos.keys()))

        repo_url, revision = _extract_repo_url_and_revision(repo_url_or_path)

        # store what we've learned
        repo_overrides.setdefault(repo_alias, {})
        repo_overrides[repo_alias]['url'] = repo_url
        repo_overrides[repo_alias]['revision'] = revision

    return repo_overrides


def _extract_repo_url_and_revision(repo_path_or_url):
    """Break up repository path/url into the repo URL and revision.

    :param repo_path_or_url: Repo URL and associated auth information. E.g.:

        * ssh://REPO_USERNAME@<GERRIT_URL>:29418/aic-clcp-manifests.git@<ref>
        * https://<GERRIT_URL>/aic-clcp-manifests.git@<ref>
        * http://<GERRIT_URL>/aic-clcp-manifests.git@<ref>
        * <LOCAL_REPO_PATH>@<ref>
        * same values as above without @<ref>

    """

    # they've forced a revision using @revision - careful not to confuse
    # this with auth
    revision = None
    try:
        if '@' in repo_path_or_url:
            # extract revision from repo URL or path
            repo_url_or_path, revision = repo_path_or_url.rsplit('@', 1)
            revision = revision[:-1] if revision.endswith('/') else revision
        else:
            repo_url_or_path = repo_path_or_url
    except Exception:
        # TODO(felipemonteiro): Use internal exceptions for this.
        raise click.ClickException(_INVALID_FORMAT_MSG % repo_path_or_url)

    return repo_url_or_path, revision


def _handle_repository(repo_url_or_path, *args, **kwargs):
    """Clone remote remote (if ``repo_url_or_path`` is a remote URL) and
    checkout specified reference .

    """

    try:
        return util.git.git_handler(repo_url_or_path, *args, **kwargs)
    except exceptions.GitException as e:
        raise click.ClickException(e)
    except Exception as e:
        LOG.exception('Unknown exception was raised during git clone/checkout:'
                      ' %s', e)
        # TODO(felipemonteiro): Use internal exceptions for this.
        raise click.ClickException(e)
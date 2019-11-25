# Copyright 2019 AT&T Intellectual Property.  All other rights reserved.
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

import click

from pegleg import config
from pegleg import engine
from pegleg import pegleg_main

LOG = logging.getLogger(__name__)


# Callbacks #
def process_repositories_callback(ctx, param, value):
    """Convenient callback for ``@click.argument(site_name)``.

    Automatically processes repository information for the specified site. This
    entails cloning all requires repositories and checking out specified
    references for each repository.
    """
    engine.repository.process_repositories(value)
    return value


def collection_default_callback(ctx, param, value):
    LOG.debug('Evaluating %s: %s', param.name, value)
    if not value:
        return ctx.params['site_name']
    return value


def decrypt_repos(site_name):
    repo_list = config.all_repos()
    for repo in repo_list:
        pegleg_main.run_decrypt(True, repo, None, site_name)


# Arguments #
SITE_REPOSITORY_ARGUMENT = click.argument(
    'site_name', callback=process_repositories_callback, is_eager=True)

# Options #
ALLOW_MISSING_SUBSTITUTIONS_OPTION = click.option(
    '-f',
    '--fail-on-missing-sub-src',
    required=False,
    type=click.BOOL,
    default=True,
    show_default=True,
    help='Raise Deckhand exception on missing substition sources.')

EXCLUDE_LINT_OPTION = click.option(
    '-x',
    '--exclude',
    'exclude_lint',
    multiple=True,
    help='Excludes specified linting checks. Warnings will still be issued. '
    '-w takes priority over -x.')

EXTRA_REPOSITORY_OPTION = click.option(
    '-e',
    '--extra-repository',
    'extra_repositories',
    multiple=True,
    help='Path or URL of additional repositories. These should be named per '
    'the site-definition file, e.g. -e global=/opt/global -e '
    'secrets=/opt/secrets. By default, the revision specified in the '
    'site-definition for the site will be leveraged but can be '
    'overridden using -e global=/opt/global@revision.')

MAIN_REPOSITORY_OPTION = click.option(
    '-r',
    '--site-repository',
    'site_repository',
    required=True,
    help='Path or URL to the primary repository (containing '
    'site_definition.yaml) repo.')

OUTPUT_STREAM_OPTION = click.option(
    '-o', '--output', 'output_stream', help='Where to output.')

REPOSITORY_CLONE_PATH_OPTION = click.option(
    '-p',
    '--clone-path',
    'clone_path',
    help='The path where the repo will be cloned. By default the repo will be '
    'cloned to the /tmp path. If this option is '
    'included and the repo already '
    'exists, then the repo will not be cloned again and the '
    'user must specify a new clone path or pass in the local copy '
    'of the repository as the site repository. Suppose the repo '
    'name is airship/treasuremap and the clone path is '
    '/tmp/mypath then the following directory is '
    'created /tmp/mypath/airship/treasuremap '
    'which will contain the contents of the repo')

REPOSITORY_KEY_OPTION = click.option(
    '-k',
    '--repo-key',
    'repo_key',
    help='The SSH public key to use when cloning remote authenticated '
    'repositories.')

REPOSITORY_USERNAME_OPTION = click.option(
    '-u',
    '--repo-username',
    'repo_username',
    help='The SSH username to use when cloning remote authenticated '
    'repositories specified in the site-definition file. Any '
    'occurrences of REPO_USERNAME will be replaced with this '
    'value.\n'
    'Use only if REPO_USERNAME appears in a repo URL.')

WARN_LINT_OPTION = click.option(
    '-w',
    '--warn',
    'warn_lint',
    multiple=True,
    help='Warn if linting check fails. -w takes priority over -x.')

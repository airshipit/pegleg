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
import sys

import click

from pegleg import config
from pegleg import engine

LOG = logging.getLogger(__name__)

LOG_FORMAT = '%(asctime)s %(levelname)-8s %(name)s:%(funcName)s [%(lineno)3d] %(message)s'  # noqa

CONTEXT_SETTINGS = {
    'help_option_names': ['-h', '--help'],
}


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option(
    '-v',
    '--verbose',
    is_flag=bool,
    default=False,
    help='Enable debug logging')
def main(*, verbose):
    if verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    logging.basicConfig(format=LOG_FORMAT, level=log_level)


@main.group(help='Commands related to sites')
@click.option(
    '-r',
    '--site-repository',
    'site_repository',
    required=True,
    help=
    'Path or URL to the primary repository (containing site_definition.yaml) '
    'repo.')
@click.option(
    '-e',
    '--extra-repository',
    'extra_repositories',
    multiple=True,
    help='Path or URL of additional repositories. These should be named per '
    'the site-definition file, e.g. -e global=/opt/global -e '
    'secrets=/opt/secrets. By default, the revision specified in the '
    'site-definition for the site will be leveraged but can be overridden '
    'using -e global=/opt/global@revision.')
@click.option(
    '-k',
    '--repo-key',
    'repo_key',
    help='The SSH public key to use when cloning remote authenticated '
    'repositories.')
@click.option(
    '-u',
    '--repo-username',
    'repo_username',
    help=
    'The SSH username to use when cloning remote authenticated repositories '
    'specified in the site-definition file. Any occurrences of REPO_USERNAME '
    'will be replaced with this value.')
def site(*, site_repository, extra_repositories, repo_key, repo_username):
    config.set_site_repo(site_repository)
    config.set_extra_repo_store(extra_repositories or [])
    config.set_repo_key(repo_key)
    config.set_repo_username(repo_username)


@site.command(help='Output complete config for one site')
@click.option(
    '-s',
    '--save-location',
    'save_location',
    help='Directory to output the complete site definition. Created '
    'automatically if it does not already exist.')
@click.option(
    '--validate',
    'validate',
    is_flag=True,
    # TODO(felipemonteiro): Potentially set this to True in the future. This
    # is currently set to False to skip validation by default for backwards
    # compatibility concerns.
    default=False,
    help='Perform validations on documents prior to collection.')
@click.option(
    '-x',
    '--exclude',
    'exclude_lint',
    multiple=True,
    help='Excludes specified linting checks. Warnings will still be issued. '
    '-w takes priority over -x.')
@click.option(
    '-w',
    '--warn',
    'warn_lint',
    multiple=True,
    help='Warn if linting check fails. -w takes priority over -x.')
@click.argument('site_name')
def collect(*, save_location, validate, exclude_lint, warn_lint, site_name):
    """Collects documents into a single site-definition.yaml file, which
    defines the entire site definition and contains all documents required
    for ingestion by Airship.

    If ``save_location`` isn't specified, then the output is directed to
    stdout.

    Collect can lint documents prior to collection if the ``--validate``
    flag is optionally included.
    """

    engine.repository.process_repositories(site_name)

    if validate:
        # Lint the primary repo prior to document collection.
        _lint(
            fail_on_missing_sub_src=True,
            exclude_lint=exclude_lint,
            warn_lint=warn_lint)
    engine.site.collect(site_name, save_location)


@site.command('list', help='List known sites')
@click.option(
    '-o',
    '--output',
    'output_stream',
    type=click.File(mode='w'),
    default=sys.stdout,
    help='Where to output')
def list_(*, output_stream):
    engine.repository.process_site_repository(update_config=True)
    engine.site.list_(output_stream)


@site.command(help='Show details for one site')
@click.option(
    '-o',
    '--output',
    'output_stream',
    type=click.File(mode='w'),
    default=sys.stdout,
    help='Where to output')
@click.argument('site_name')
def show(*, output_stream, site_name):
    engine.repository.process_repositories(site_name)
    engine.site.show(site_name, output_stream)


@site.command('render', help='Render a site through the deckhand engine')
@click.option(
    '-o',
    '--output',
    'output_stream',
    type=click.File(mode='w'),
    default=sys.stdout,
    help='Where to output')
@click.argument('site_name')
def render(*, output_stream, site_name):
    engine.repository.process_repositories(site_name)
    engine.site.render(site_name, output_stream)


@site.command('lint', help='Lint a site')
@click.option(
    '-f',
    '--fail-on-missing-sub-src',
    'fail_on_missing_sub_src',
    required=False,
    type=click.BOOL,
    default=True,
    help='Fail when there is missing substitution source.')
@click.option(
    '-x',
    '--exclude',
    'exclude_lint',
    multiple=True,
    help='Excludes specified linting checks. Warnings will still be issued. '
    '-w takes priority over -x.')
@click.option(
    '-w',
    '--warn',
    'warn_lint',
    multiple=True,
    help='Warn if linting check fails. -w takes priority over -x.')
@click.argument('site_name')
def lint(*, fail_on_missing_sub_src, exclude_lint, warn_lint, site_name):
    engine.repository.process_repositories(site_name)
    _lint(
        fail_on_missing_sub_src=fail_on_missing_sub_src,
        exclude_lint=exclude_lint,
        warn_lint=warn_lint)


def _validate_revision_callback(_ctx, _param, value):
    if value is not None and value.startswith('v'):
        return value
    else:
        raise click.BadParameter('revisions must start with "v"')


@main.group(help='Create directory structure and stubs')
def stub():
    pass


RELEASE_OPTION = click.option(
    '-r',
    '--revision',
    callback=_validate_revision_callback,
    required=True,
    help='Configuration revision to use (e.g. v1.0)')

SITE_TYPE_OPTION = click.option(
    '-t',
    '--site-type',
    required=True,
    help='Site type to use ("large", "medium", "cicd", "labs", etc.')

LINT_OPTION = click.option(
    '-f',
    '--fail-on-missing-sub-src',
    required=False,
    type=click.BOOL,
    default=True,
    help=
    "Raise deckhand exception on missing substition sources. Defaults to True."
)


@stub.command('global', help='Add global structure for a new revision')
@RELEASE_OPTION
def global_(*, revision):
    engine.stub.global_(revision)


@stub.command(help='Add a new site + revision')
@click.argument('site_name')
@RELEASE_OPTION
@SITE_TYPE_OPTION
def site(*, revision, site_type, site_name):
    engine.stub.site(revision, site_type, site_name)


@stub.command('site-type', help='Add a new site-type + revision')
@RELEASE_OPTION
@SITE_TYPE_OPTION
def site_type(*, revision, site_type):
    engine.stub.site_type(revision, site_type)


def _lint(*, fail_on_missing_sub_src, exclude_lint, warn_lint):
    warns = engine.lint.full(fail_on_missing_sub_src, exclude_lint, warn_lint)
    if warns:
        click.echo("Linting passed, but produced some warnings.")
        for w in warns:
            click.echo(w)

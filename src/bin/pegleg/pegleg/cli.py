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

from . import engine
from pegleg import config

import click
import logging
import sys

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
    '-p',
    '--primary',
    'primary_repo',
    required=True,
    help=
    'Path to the root of the primary (containing site_definition.yaml) repo.')
@click.option(
    '-a',
    '--auxiliary',
    'aux_repo',
    multiple=True,
    help='Path to the root of an auxiliary repo.')
def site(primary_repo, aux_repo):
    config.set_primary_repo(primary_repo)
    config.set_auxiliary_repo_list(aux_repo or [])


@site.command(help='Output complete config for one site')
@click.option(
    '-s',
    '--save-location',
    'save_location',
    type=click.Path(
        file_okay=False, dir_okay=True, writable=True, resolve_path=True),
    default=sys.stdout,
    help='Where to output')
@click.argument('site_name')
def collect(*, save_location, site_name):
    engine.site.collect(site_name, save_location)


@site.command(help='Find sites impacted by changed files')
@click.option(
    '-i',
    '--input',
    'input_stream',
    type=click.File(mode='r'),
    default=sys.stdin,
    help='List of impacted files')
@click.option(
    '-o',
    '--output',
    'output_stream',
    type=click.File(mode='w'),
    default=sys.stdout)
def impacted(*, input_stream, output_stream):
    engine.site.impacted(input_stream, output_stream)


@site.command('list', help='List known sites')
@click.option(
    '-o',
    '--output',
    'output_stream',
    type=click.File(mode='w'),
    default=sys.stdout,
    help='Where to output')
def list_(*, output_stream):
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
    engine.site.render(site_name, output_stream)


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


@LINT_OPTION
@main.command(help='Sanity checks for repository content')
@click.option(
    '-p',
    '--primary',
    'primary_repo',
    required=True,
    help=
    'Path to the root of the primary (containing site_definition.yaml) repo.')
@click.option(
    '-a',
    '--auxiliary',
    'aux_repo',
    multiple=True,
    help='Path to the root of a auxiliary repo.')
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
def lint(*, fail_on_missing_sub_src, primary_repo, aux_repo, exclude_lint,
         warn_lint):
    config.set_primary_repo(primary_repo)
    config.set_auxiliary_repo_list(aux_repo or [])
    warns = engine.lint.full(fail_on_missing_sub_src, exclude_lint, warn_lint)
    if warns:
        click.echo("Linting passed, but produced some warnings.")
        for w in warns:
            click.echo(w)

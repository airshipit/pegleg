from . import engine
import click
import logging
import sys

LOG = logging.getLogger(__name__)

LOG_FORMAT = '%(asctime)s %(levelname)-8s %(name)s:%(funcName)s [%(lineno)3d] %(message)s'  # noqa

CONTEXT_SETTINGS = {
    'help_option_names': ['-h', '--help'],
}


@click.group(context_settings=CONTEXT_SETTINGS)
@click.pass_context
@click.option(
    '-v',
    '--verbose',
    is_flag=bool,
    default=False,
    help='Enable debug logging')
def main(ctx, *, verbose):
    if verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.INFO
    logging.basicConfig(format=LOG_FORMAT, level=log_level)


@main.group(help='Commands related to sites')
def site():
    pass


@site.command(help='Output complete config for one site')
@click.option(
    '-o',
    '--output',
    'output_stream',
    type=click.File(mode='w'),
    default=sys.stdout,
    help='Where to output')
@click.argument('site_name')
def collect(*, output_stream, site_name):
    engine.site.collect(site_name, output_stream)


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


@main.command(help='Sanity checks for repository content')
def lint():
    engine.lint.full()

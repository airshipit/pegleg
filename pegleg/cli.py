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

import functools
import logging
import os

import click

from pegleg import config
from pegleg import engine
from pegleg.engine import bundle
from pegleg.engine import catalog
from pegleg.engine.secrets import wrap_secret
from pegleg.engine.util import files
from pegleg.engine.util.shipyard_helper import ShipyardHelper

LOG = logging.getLogger(__name__)

LOG_FORMAT = '%(asctime)s %(levelname)-8s %(name)s:%(funcName)s [%(lineno)3d] %(message)s'  # noqa

CONTEXT_SETTINGS = {
    'help_option_names': ['-h', '--help'],
}


def _process_repositories_callback(ctx, param, value):
    """Convenient callback for ``@click.argument(site_name)``.

    Automatically processes repository information for the specified site. This
    entails cloning all requires repositories and checking out specified
    references for each repository.
    """
    engine.repository.process_repositories(value)
    return value


MAIN_REPOSITORY_OPTION = click.option(
    '-r',
    '--site-repository',
    'site_repository',
    required=True,
    help='Path or URL to the primary repository (containing '
    'site_definition.yaml) repo.')

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

WARN_LINT_OPTION = click.option(
    '-w',
    '--warn',
    'warn_lint',
    multiple=True,
    help='Warn if linting check fails. -w takes priority over -x.')

SITE_REPOSITORY_ARGUMENT = click.argument(
    'site_name', callback=_process_repositories_callback)


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option('-v',
              '--verbose',
              is_flag=True,
              default=False,
              help='Enable debug logging')
def main(*, verbose):
    """Main CLI meta-group, which includes the following groups:

    * site: site-level actions
    * repo: repository-level actions

    """

    if verbose:
        log_level = logging.DEBUG
    else:
        log_level = logging.ERROR
    logging.basicConfig(format=LOG_FORMAT, level=log_level)


@main.group(help='Commands related to repositories')
@MAIN_REPOSITORY_OPTION
@REPOSITORY_CLONE_PATH_OPTION
# TODO(felipemonteiro): Support EXTRA_REPOSITORY_OPTION as well to be
# able to lint multiple repos together.
@REPOSITORY_USERNAME_OPTION
@REPOSITORY_KEY_OPTION
def repo(*, site_repository, clone_path, repo_key, repo_username):
    """Group for repo-level actions, which include:

    * lint: lint all sites across the repository

    """

    config.set_site_repo(site_repository)
    config.set_clone_path(clone_path)
    config.set_repo_key(repo_key)
    config.set_repo_username(repo_username)
    config.set_umask()


def _lint_helper(*,
                 fail_on_missing_sub_src,
                 exclude_lint,
                 warn_lint,
                 site_name=None):
    """Helper for executing lint on specific site or all sites in repo."""
    if site_name:
        func = functools.partial(engine.lint.site, site_name=site_name)
    else:
        func = engine.lint.full
    warns = func(fail_on_missing_sub_src=fail_on_missing_sub_src,
                 exclude_lint=exclude_lint,
                 warn_lint=warn_lint)
    if warns:
        click.echo("Linting passed, but produced some warnings.")
        for w in warns:
            click.echo(w)


@repo.command('lint', help='Lint all sites in a repository')
@ALLOW_MISSING_SUBSTITUTIONS_OPTION
@EXCLUDE_LINT_OPTION
@WARN_LINT_OPTION
def lint_repo(*, fail_on_missing_sub_src, exclude_lint, warn_lint):
    """Lint all sites using checks defined in :mod:`pegleg.engine.errorcodes`.
    """
    engine.repository.process_site_repository(update_config=True)
    _lint_helper(fail_on_missing_sub_src=fail_on_missing_sub_src,
                 exclude_lint=exclude_lint,
                 warn_lint=warn_lint)


@main.group(help='Commands related to sites')
@MAIN_REPOSITORY_OPTION
@REPOSITORY_CLONE_PATH_OPTION
@EXTRA_REPOSITORY_OPTION
@REPOSITORY_USERNAME_OPTION
@REPOSITORY_KEY_OPTION
def site(*, site_repository, clone_path, extra_repositories, repo_key,
         repo_username):
    """Group for site-level actions, which include:

    * list: list available sites in a manifests repo
    * lint: lint a site along with all its dependencies
    * render: render a site using Deckhand
    * show: show a site's files

    """

    config.set_site_repo(site_repository)
    config.set_clone_path(clone_path)
    config.set_extra_repo_overrides(extra_repositories or [])
    config.set_repo_key(repo_key)
    config.set_repo_username(repo_username)
    config.set_umask()


@site.command(help='Output complete config for one site')
@click.option('-s',
              '--save-location',
              'save_location',
              help='Directory to output the complete site definition. Created '
              'automatically if it does not already exist.')
@click.option(
    '--validate/--no-validate',
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
@click.option('-w',
              '--warn',
              'warn_lint',
              multiple=True,
              help='Warn if linting check fails. -w takes priority over -x.')
@SITE_REPOSITORY_ARGUMENT
def collect(*, save_location, validate, exclude_lint, warn_lint, site_name):
    """Collects documents into a single site-definition.yaml file, which
    defines the entire site definition and contains all documents required
    for ingestion by Airship.

    If ``save_location`` isn't specified, then the output is directed to
    stdout.

    Collect can lint documents prior to collection if the ``--validate``
    flag is optionally included.
    """
    if validate:
        # Lint the primary repo prior to document collection.
        _lint_helper(site_name=site_name,
                     fail_on_missing_sub_src=True,
                     exclude_lint=exclude_lint,
                     warn_lint=warn_lint)
    engine.site.collect(site_name, save_location)


@site.command('list', help='List known sites')
@click.option('-o', '--output', 'output_stream', help='Where to output.')
def list_sites(*, output_stream):
    engine.repository.process_site_repository(update_config=True)
    engine.site.list_(output_stream)


@site.command(help='Show details for one site')
@click.option('-o', '--output', 'output_stream', help='Where to output.')
@SITE_REPOSITORY_ARGUMENT
def show(*, output_stream, site_name):
    engine.site.show(site_name, output_stream)


@site.command('render', help='Render a site through the deckhand engine')
@click.option('-o', '--output', 'output_stream', help='Where to output.')
@click.option(
    '-v',
    '--validate',
    'validate',
    is_flag=True,
    default=True,
    show_default=True,
    help='Whether to pre-validate documents using built-in schema validation. '
    'Skips over externally registered DataSchema documents to avoid '
    'false positives.')
@SITE_REPOSITORY_ARGUMENT
def render(*, output_stream, site_name, validate):
    engine.site.render(site_name, output_stream, validate)


@site.command('lint', help='Lint a given site in a repository')
@ALLOW_MISSING_SUBSTITUTIONS_OPTION
@EXCLUDE_LINT_OPTION
@WARN_LINT_OPTION
@SITE_REPOSITORY_ARGUMENT
def lint_site(*, fail_on_missing_sub_src, exclude_lint, warn_lint, site_name):
    """Lint a given site using checks defined in
    :mod:`pegleg.engine.errorcodes`.
    """
    _lint_helper(site_name=site_name,
                 fail_on_missing_sub_src=fail_on_missing_sub_src,
                 exclude_lint=exclude_lint,
                 warn_lint=warn_lint)


def collection_default_callback(ctx, param, value):
    LOG.debug('Evaluating %s: %s', param.name, value)
    if not value:
        return ctx.params['site_name']
    return value


@site.command('upload', help='Upload documents to Shipyard')
# Keystone authentication parameters
@click.option('--os-project-domain-name',
              envvar='OS_PROJECT_DOMAIN_NAME',
              required=False,
              default='default')
@click.option('--os-user-domain-name',
              envvar='OS_USER_DOMAIN_NAME',
              required=False,
              default='default')
@click.option('--os-project-name', envvar='OS_PROJECT_NAME', required=False)
@click.option('--os-username', envvar='OS_USERNAME', required=False)
@click.option('--os-password', envvar='OS_PASSWORD', required=False)
@click.option('--os-auth-url', envvar='OS_AUTH_URL', required=False)
@click.option('--os-auth-token', envvar='OS_AUTH_TOKEN', required=False)
# Option passed to Shipyard client context
@click.option(
    '--context-marker',
    help='Specifies a UUID (8-4-4-4-12 format) that will be used to correlate '
    'logs, transactions, etc. in downstream activities triggered by this '
    'interaction ',
    required=False,
    type=click.UUID)
@click.option(
    '-b',
    '--buffer-mode',
    'buffer_mode',
    required=False,
    default='replace',
    show_default=True,
    type=click.Choice(['append', 'replace']),
    help='Set the buffer mode when uploading documents. Supported buffer '
    'modes include append, replace, auto.\n'
    'append: Add the collection to the Shipyard Buffer, only if that '
    'collection does not already exist in the Shipyard buffer.\n'
    'replace: Clear the Shipyard Buffer before adding the specified '
    'collection.\n')
@click.option('--collection',
              'collection',
              help='Specifies the name to use for the uploaded collection. '
              'Defaults to the specified `site_name`.',
              callback=collection_default_callback)
@SITE_REPOSITORY_ARGUMENT
@click.pass_context
def upload(ctx, *, os_project_domain_name, os_user_domain_name,
           os_project_name, os_username, os_password, os_auth_url,
           os_auth_token, context_marker, site_name, buffer_mode, collection):
    if not ctx.obj:
        ctx.obj = {}

    # Build API parameters required by Shipyard API Client.
    if os_auth_token:
        os.environ['OS_AUTH_TOKEN'] = os_auth_token
        auth_vars = {'os_auth_token': os_auth_token}
    else:
        auth_vars = {
            'project_domain_name': os_project_domain_name,
            'user_domain_name': os_user_domain_name,
            'project_name': os_project_name,
            'username': os_username,
            'password': os_password,
            'auth_url': os_auth_url
        }

    ctx.obj['API_PARAMETERS'] = {'auth_vars': auth_vars}
    ctx.obj['context_marker'] = str(context_marker)
    ctx.obj['site_name'] = site_name
    ctx.obj['collection'] = collection

    click.echo(ShipyardHelper(ctx, buffer_mode).upload_documents())


@site.group(name='secrets', help='Commands to manage site secrets documents')
def secrets():
    pass


@secrets.command(
    'generate-pki',
    help='Generate certificates and keys according to all PKICatalog '
    'documents in the site. Regenerating certificates can be '
    'accomplished by re-running this command.')
@click.option(
    '-a',
    '--author',
    'author',
    help='Identifying name of the author generating new certificates. Used'
    'for tracking provenance information in the PeglegManagedDocuments. '
    'An attempt is made to automatically determine this value, '
    'but should be provided.')
@click.option('-d',
              '--days',
              'days',
              default=365,
              show_default=True,
              help='Duration in days generated certificates should be valid.')
@click.argument('site_name')
def generate_pki(site_name, author, days):
    """Generate certificates, certificate authorities and keypairs for a given
    site.

    """

    engine.repository.process_repositories(site_name, overwrite_existing=True)
    pkigenerator = catalog.pki_generator.PKIGenerator(site_name,
                                                      author=author,
                                                      duration=days)
    output_paths = pkigenerator.generate()

    click.echo("Generated PKI files written to:\n%s" % '\n'.join(output_paths))


@secrets.command(
    'wrap',
    help='Wrap bare files (e.g. pem or crt) in a PeglegManagedDocument '
    'and encrypt them (by default).')
@click.option('-a',
              '--author',
              'author',
              help='Author for the new wrapped file.')
@click.option('--filename',
              'filename',
              help='The relative file path for the file to be wrapped.')
@click.option(
    '-o',
    '--output-path',
    'output_path',
    required=False,
    help='The output path for the wrapped file. (default: input path with '
    '.yaml)')
@click.option('-s',
              '--schema',
              'schema',
              help='The schema for the document to be wrapped, e.g. '
              'deckhand/Certificate/v1')
@click.option('-n',
              '--name',
              'name',
              help='The name for the document to be wrapped, e.g. new-cert')
@click.option('-l',
              '--layer',
              'layer',
              help='The layer for the document to be wrapped., e.g. site.')
@click.option('--encrypt/--no-encrypt',
              'encrypt',
              is_flag=True,
              default=True,
              show_default=True,
              help='Whether to encrypt the wrapped file.')
@click.argument('site_name')
def wrap_secret_cli(*, site_name, author, filename, output_path, schema, name,
                    layer, encrypt):
    """Wrap a bare secrets file in a YAML and ManagedDocument.

    """

    engine.repository.process_repositories(site_name, overwrite_existing=True)
    wrap_secret(author,
                filename,
                output_path,
                schema,
                name,
                layer,
                encrypt,
                site_name=site_name)


@site.command('genesis_bundle',
              help='Construct the genesis deployment bundle.')
@click.option('-b',
              '--build-dir',
              'build_dir',
              type=click.Path(file_okay=False,
                              dir_okay=True,
                              resolve_path=True),
              required=True,
              help='Destination directory to store the genesis bundle.')
@click.option(
    '--include-validators',
    'validators',
    is_flag=True,
    default=False,
    help='A flag to request generate genesis validation scripts in addition '
    'to genesis.sh script.')
@SITE_REPOSITORY_ARGUMENT
def genesis_bundle(*, build_dir, validators, site_name):
    encryption_key = os.environ.get("PROMENADE_ENCRYPTION_KEY")
    bundle.build_genesis(build_dir, encryption_key, validators,
                         logging.DEBUG == LOG.getEffectiveLevel(), site_name)


@secrets.command(
    'check-pki-certs',
    help='Determine if certificates in a sites PKICatalog are expired or '
    'expiring within a specified number of days.')
@click.option(
    '-d',
    '--days',
    'days',
    default=60,
    help='The number of days past today to check if certificates are valid.')
@click.argument('site_name')
def check_pki_certs(site_name, days):
    """Check PKI certificates of a site for expiration."""

    engine.repository.process_repositories(site_name, overwrite_existing=True)

    cert_results = engine.secrets.check_cert_expiry(site_name, duration=days)

    click.echo("The following certs will expire within {} days: \n{}".format(
        days, cert_results))


@main.group(help='Commands related to types')
@MAIN_REPOSITORY_OPTION
@REPOSITORY_CLONE_PATH_OPTION
@EXTRA_REPOSITORY_OPTION
@REPOSITORY_USERNAME_OPTION
@REPOSITORY_KEY_OPTION
def type(*, site_repository, clone_path, extra_repositories, repo_key,
         repo_username):
    """Group for repo-level actions, which include:

    * list: list all types across the repository

    """
    config.set_site_repo(site_repository)
    config.set_clone_path(clone_path)
    config.set_extra_repo_overrides(extra_repositories or [])
    config.set_repo_key(repo_key)
    config.set_repo_username(repo_username)


@type.command('list', help='List known types')
@click.option('-o', '--output', 'output_stream', help='Where to output.')
def list_types(*, output_stream):
    """List type names for a given repository."""
    engine.repository.process_site_repository(update_config=True)
    engine.type.list_types(output_stream)


@secrets.group(name='generate',
               help='Command group to generate site secrets documents.')
def generate():
    pass


@generate.command('passphrases', help='Command to generate site passphrases')
@click.argument('site_name')
@click.option(
    '-s',
    '--save-location',
    'save_location',
    required=True,
    help='Directory to store the generated site passphrases in. It will '
    'be created automatically, if it does not already exist. The '
    'generated, wrapped, and encrypted passphrases files will be saved '
    'in: <save_location>/site/<site_name>/secrets/passphrases/ '
    'directory.')
@click.option(
    '-a',
    '--author',
    'author',
    required=True,
    help='Identifier for the program or person who is generating the secrets '
    'documents')
@click.option('-i',
              '--interactive',
              'interactive',
              is_flag=True,
              default=False,
              help='Generate passphrases interactively, not automatically')
@click.option(
    '--force-cleartext',
    'force_cleartext',
    is_flag=True,
    default=False,
    show_default=True,
    help='Force cleartext generation of passphrases. This is not recommended.')
def generate_passphrases(*, site_name, save_location, author, interactive,
                         force_cleartext):
    engine.repository.process_repositories(site_name)
    engine.secrets.generate_passphrases(site_name, save_location, author,
                                        interactive, force_cleartext)


@secrets.command('encrypt',
                 help='Command to encrypt and wrap site secrets '
                 'documents with metadata.storagePolicy set '
                 'to encrypted, in pegleg managed documents.')
@click.option(
    '-s',
    '--save-location',
    'save_location',
    default=None,
    help='Directory to output the encrypted site secrets files. Created '
    'automatically if it does not already exist. '
    'If save_location is not provided, the output encrypted files will '
    'overwrite the original input files (default behavior)')
@click.option(
    '-a',
    '--author',
    'author',
    required=True,
    help='Identifier for the program or person who is encrypting the secrets '
    'documents')
@click.argument('site_name')
def encrypt(*, save_location, author, site_name):
    engine.repository.process_repositories(site_name, overwrite_existing=True)
    if save_location is None:
        save_location = config.get_site_repo()
    engine.secrets.encrypt(save_location, author, site_name=site_name)


@secrets.command('decrypt',
                 help='Command to unwrap and decrypt one site '
                 'secrets document and print it to stdout.')
@click.option('--path',
              'path',
              type=click.Path(exists=True, readable=True),
              required=True,
              help='The file or directory path to decrypt.')
@click.option(
    '-s',
    '--save-location',
    'save_location',
    default=None,
    help='The destination where the decrypted file(s) should be saved. '
    'If not specified, decrypted data will output to stdout.')
@click.option(
    '-o',
    '--overwrite',
    'overwrite',
    is_flag=True,
    default=False,
    help='Overwrites original file(s) at path with decrypted data when set. '
    'Overrides --save-location option.')
@click.argument('site_name')
def decrypt(*, path, save_location, overwrite, site_name):
    engine.repository.process_repositories(site_name)

    decrypted = engine.secrets.decrypt(path, site_name=site_name)
    if overwrite:
        for path, data in decrypted.items():
            files.write(data, path)
    elif save_location is None:
        for data in decrypted.values():
            click.echo(data)
    else:
        for path, data in decrypted.items():
            file_name = os.path.split(path)[1]
            file_save_location = os.path.join(save_location, file_name)
            files.write(data, file_save_location)


@main.group(help='Miscellaneous generate commands')
def generate():
    pass


@generate.command(
    'passphrase',
    help='Command to generate a passphrase and print out to stdout')
@click.option('-l',
              '--length',
              'length',
              default=24,
              show_default=True,
              help='Generate a passphrase of the given length. '
              'Length is >= 24, no maximum length.')
def generate_passphrase(length):
    click.echo('Generated Passhprase: {}'.format(
        engine.secrets.generate_crypto_string(length)))


@generate.command('salt',
                  help='Command to generate a salt and print out to stdout')
@click.option('-l',
              '--length',
              'length',
              default=24,
              show_default=True,
              help='Generate a passphrase of the given length. '
              'Length is >= 24, no maximum length.')
def generate_salt(length):
    click.echo("Generated Salt: {}".format(
        engine.secrets.generate_crypto_string(length)))

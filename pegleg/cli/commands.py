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
import warnings

import click

from pegleg.cli import utils
from pegleg import pegleg_main

LOG = logging.getLogger(__name__)

CONTEXT_SETTINGS = {
    'help_option_names': ['-h', '--help'],
}


@click.group(context_settings=CONTEXT_SETTINGS)
@click.option(
    '-v',
    '--verbose',
    is_flag=True,
    default=False,
    help='Enable debug logging')
@click.option(
    '-l',
    '--logging-level',
    'logging_level',
    default='40',
    show_default=True,
    type=click.Choice(['10', '20', '30', '40', '50']),
    help='Sets logging level where:\n'
    '10=DEBUG\n'
    '20=INFO\n'
    '30=WARNING\n'
    '40=ERROR\n'
    '50=CRITICAL')
def main(*, verbose, logging_level):
    """Main CLI meta-group, which includes the following groups:

    * site: site-level actions
    * repo: repository-level actions

    """
    pegleg_main.set_logging_level(verbose, logging_level)


@main.group(help='Commands related to repositories')
@utils.MAIN_REPOSITORY_OPTION
@utils.REPOSITORY_CLONE_PATH_OPTION
# TODO(felipemonteiro): Support EXTRA_REPOSITORY_OPTION as well to be
# able to lint multiple repos together.
@utils.REPOSITORY_USERNAME_OPTION
@utils.REPOSITORY_KEY_OPTION
def repo(*, site_repository, clone_path, repo_key, repo_username):
    """Group for repo-level actions, which include:

    * lint: lint all sites across the repository
    """
    pegleg_main.run_config(
        site_repository,
        clone_path,
        repo_key,
        repo_username, [],
        run_umask=True)


@repo.command('lint', help='Lint all sites in a repository')
@utils.ALLOW_MISSING_SUBSTITUTIONS_OPTION
@utils.EXCLUDE_LINT_OPTION
@utils.WARN_LINT_OPTION
def lint_repo(*, fail_on_missing_sub_src, exclude_lint, warn_lint):
    """Lint all sites using checks defined in :mod:`pegleg.engine.errorcodes`.
    """
    warns = pegleg_main.run_lint(
        exclude_lint, fail_on_missing_sub_src, warn_lint)
    if warns:
        click.echo("Linting passed, but produced some warnings.")
        for w in warns:
            click.echo(w)


@main.group(help='Commands related to sites')
@utils.MAIN_REPOSITORY_OPTION
@utils.REPOSITORY_CLONE_PATH_OPTION
@utils.EXTRA_REPOSITORY_OPTION
@utils.REPOSITORY_USERNAME_OPTION
@utils.REPOSITORY_KEY_OPTION
@click.option(
    '--decrypt/--no-decrypt',
    'decrypt_repos',
    default=True,
    help='Automatically attempts to decrypt repositories before executing '
    'the command. Decryption will happen after repositories are copied to '
    'the temporary directory created by pegleg or the user specified '
    '`-p` directory. This means in most situations, pre-command decrypt '
    'will not overwrite existing files. For overwriting existing files, '
    'the full decrypt command should still be used.')
def site(
        *, site_repository, clone_path, extra_repositories, repo_key,
        repo_username, decrypt_repos):
    """Group for site-level actions, which include:

    * list: list available sites in a manifests repo
    * lint: lint a site along with all its dependencies
    * render: render a site using Deckhand
    * show: show a site's files

    """
    pegleg_main.run_config(
        site_repository,
        clone_path,
        repo_key,
        repo_username,
        extra_repositories or [],
        run_umask=True,
        decrypt_repos=decrypt_repos)


@site.command(help='Output complete config for one site')
@click.option(
    '-s',
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
@utils.EXCLUDE_LINT_OPTION
@utils.WARN_LINT_OPTION
@utils.SITE_REPOSITORY_ARGUMENT
def collect(*, save_location, validate, exclude_lint, warn_lint, site_name):
    """Collects documents into a single site-definition.yaml file, which
    defines the entire site definition and contains all documents required
    for ingestion by Airship.

    If ``save_location`` isn't specified, then the output is directed to
    stdout.

    Collect can lint documents prior to collection if the ``--validate``
    flag is optionally included.
    """
    pegleg_main.run_collect(
        exclude_lint, save_location, site_name, validate, warn_lint)


@site.command('list', help='List known sites')
@utils.OUTPUT_STREAM_OPTION
def list_sites(*, output_stream):
    pegleg_main.run_list_sites(output_stream)


@site.command(help='Show details for one site')
@utils.OUTPUT_STREAM_OPTION
@utils.SITE_REPOSITORY_ARGUMENT
def show(*, output_stream, site_name):
    pegleg_main.run_show(output_stream, site_name)


@site.command('render', help='Render a site through the deckhand engine')
@utils.OUTPUT_STREAM_OPTION
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
@utils.SITE_REPOSITORY_ARGUMENT
def render(*, output_stream, site_name, validate):
    pegleg_main.run_render(output_stream, site_name, validate)


@site.command('lint', help='Lint a given site in a repository')
@utils.ALLOW_MISSING_SUBSTITUTIONS_OPTION
@utils.EXCLUDE_LINT_OPTION
@utils.WARN_LINT_OPTION
@utils.SITE_REPOSITORY_ARGUMENT
def lint_site(*, fail_on_missing_sub_src, exclude_lint, warn_lint, site_name):
    """Lint a given site using checks defined in
    :mod:`pegleg.engine.errorcodes`.
    """
    warns = pegleg_main.run_lint_site(
        exclude_lint, fail_on_missing_sub_src, site_name, warn_lint)
    if warns:
        click.echo("Linting passed, but produced some warnings.")
        for w in warns:
            click.echo(w)


@site.command('upload', help='Upload documents to Shipyard')
# Keystone authentication parameters
@click.option('--os-domain-name', envvar='OS_DOMAIN_NAME', required=False)
@click.option(
    '--os-project-domain-name',
    envvar='OS_PROJECT_DOMAIN_NAME',
    required=False,
    default='default')
@click.option(
    '--os-user-domain-name',
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
@click.option(
    '--collection',
    'collection',
    help='Specifies the name to use for the uploaded collection. '
    'Defaults to the specified `site_name`.',
    callback=utils.collection_default_callback)
@utils.SITE_REPOSITORY_ARGUMENT
@click.pass_context
def upload(
        ctx, *, os_domain_name, os_project_domain_name, os_user_domain_name,
        os_project_name, os_username, os_password, os_auth_url, os_auth_token,
        context_marker, site_name, buffer_mode, collection):
    resp = pegleg_main.run_upload(
        buffer_mode, collection, context_marker, ctx, os_auth_token,
        os_auth_url, os_domain_name, os_password, os_project_domain_name,
        os_project_name, os_user_domain_name, os_username, site_name)
    click.echo(resp)


@site.group(name='secrets', help='Commands to manage site secrets documents')
def secrets():
    pass


@secrets.command(
    'generate-pki',
    short_help='[DEPRECATED - Use secrets generate certificates]\n'
    'Generate certs and keys according to the site PKICatalog',
    help='[DEPRECATED - Use secrets generate certificates]\n'
    'Generate certificates and keys according to all PKICatalog '
    'documents in the site using the PKI module. The default behavior is '
    'to generate all certificates that are not yet present. For example, '
    'the first time generate PKI is run or when new entries are added '
    'to the PKICatalogue, only those new entries will be generated on '
    'subsequent runs.')
@click.option(
    '-a',
    '--author',
    'author',
    help='Identifying name of the author generating new certificates. Used '
    'for tracking provenance information in the PeglegManagedDocuments. '
    'An attempt is made to automatically determine this value, '
    'but should be provided.')
@click.option(
    '-d',
    '--days',
    'days',
    default=365,
    show_default=True,
    help='Duration in days generated certificates should be valid.')
@click.option(
    '--regenerate-all',
    'regenerate_all',
    is_flag=True,
    default=False,
    show_default=True,
    help='Force Pegleg to regenerate all PKI items.')
@utils.SITE_REPOSITORY_ARGUMENT
def generate_pki_deprecated(site_name, author, days, regenerate_all):
    """Generate certificates, certificate authorities and keypairs for a given
    site.

    """
    warnings.warn(
        "DEPRECATED - Use secrets generate certificates", DeprecationWarning)
    output_paths = pegleg_main.run_generate_pki(
        author, days, regenerate_all, site_name)

    click.echo("Generated PKI files written to:\n%s" % '\n'.join(output_paths))


@secrets.command(
    'wrap',
    help='Wrap bare files (e.g. pem or crt) in a PeglegManagedDocument '
    'and encrypt them (by default).')
@click.option(
    '-a', '--author', 'author', help='Author for the new wrapped file.')
@click.option(
    '--filename',
    'filename',
    help='The relative file path for the file to be wrapped.')
@click.option(
    '-o',
    '--output-path',
    'output_path',
    required=False,
    help='The output path for the wrapped file. (default: input path with '
    '.yaml)')
@click.option(
    '-s',
    '--schema',
    'schema',
    help='The schema for the document to be wrapped, e.g. '
    'deckhand/Certificate/v1')
@click.option(
    '-n',
    '--name',
    'name',
    help='The name for the document to be wrapped, e.g. new-cert')
@click.option(
    '-l',
    '--layer',
    'layer',
    help='The layer for the document to be wrapped., e.g. site.')
@click.option(
    '--encrypt/--no-encrypt',
    'encrypt',
    is_flag=True,
    default=True,
    show_default=True,
    help='Whether to encrypt the wrapped file.')
@utils.SITE_REPOSITORY_ARGUMENT
def wrap_secret_cli(
        *, site_name, author, filename, output_path, schema, name, layer,
        encrypt):
    """Wrap a bare secrets file in a YAML and ManagedDocument"""
    pegleg_main.run_wrap_secret(
        author, encrypt, filename, layer, name, output_path, schema, site_name)


@site.command(
    'genesis_bundle', help='Construct the genesis deployment bundle.')
@click.option(
    '-b',
    '--build-dir',
    'build_dir',
    type=click.Path(file_okay=False, dir_okay=True, resolve_path=True),
    required=True,
    help='Destination directory to store the genesis bundle.')
@click.option(
    '--include-validators',
    'validators',
    is_flag=True,
    default=False,
    help='A flag to request generate genesis validation scripts in addition '
    'to genesis.sh script.')
@utils.SITE_REPOSITORY_ARGUMENT
def genesis_bundle(*, build_dir, validators, site_name):
    pegleg_main.run_genesis_bundle(build_dir, site_name, validators)


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
@utils.SITE_REPOSITORY_ARGUMENT
def check_pki_certs(site_name, days):
    """Check PKI certificates of a site for expiration."""
    expiring_certs_exist, cert_results = pegleg_main.run_check_pki_certs(
        days, site_name)

    if expiring_certs_exist:
        click.echo(
            "The following certs will expire within the next {} days: \n{}".
            format(days, cert_results))
        exit(1)
    else:
        click.echo(
            "No certificates will expire within the next {} days.".format(
                days))
        exit(0)


@main.group(help='Commands related to types')
@utils.MAIN_REPOSITORY_OPTION
@utils.REPOSITORY_CLONE_PATH_OPTION
@utils.EXTRA_REPOSITORY_OPTION
@utils.REPOSITORY_USERNAME_OPTION
@utils.REPOSITORY_KEY_OPTION
def type(
        *, site_repository, clone_path, extra_repositories, repo_key,
        repo_username):
    """Group for repo-level actions, which include:

    * list: list all types across the repository

    """
    pegleg_main.run_config(
        site_repository,
        clone_path,
        repo_key,
        repo_username,
        extra_repositories or [],
        run_umask=False)


@type.command('list', help='List known types')
@utils.OUTPUT_STREAM_OPTION
def list_types(*, output_stream):
    """List type names for a given repository."""
    pegleg_main.run_list_types(output_stream)


@secrets.group(
    name='generate', help='Command group to generate site secrets documents.')
def generate():
    pass


@generate.command(
    'certificates',
    short_help='Generate certs and keys according to the site PKICatalog',
    help='Generate certificates and keys according to all PKICatalog '
    'documents in the site using the PKI module. The default behavior is '
    'to generate all certificates that are not yet present. For example, '
    'the first time generate PKI is run or when new entries are added '
    'to the PKICatalogue, only those new entries will be generated on '
    'subsequent runs.')
@click.option(
    '-a',
    '--author',
    'author',
    help='Identifying name of the author generating new certificates. Used'
    'for tracking provenance information in the PeglegManagedDocuments. '
    'An attempt is made to automatically determine this value, '
    'but should be provided.')
@click.option(
    '-d',
    '--days',
    'days',
    default=365,
    show_default=True,
    help='Duration in days generated certificates should be valid.')
@click.option(
    '--regenerate-all',
    'regenerate_all',
    is_flag=True,
    default=False,
    show_default=True,
    help='Force Pegleg to regenerate all PKI items.')
@click.option(
    '-s',
    '--save-location',
    'save_location',
    required=False,
    help='Directory to store the generated site certificates in. It will '
    'be created automatically, if it does not already exist. The '
    'generated, wrapped, and encrypted passphrases files will be saved '
    'in: <save_location>/site/<site_name>/secrets/certificates/ '
    'directory. Defaults to site repository path if no value given.')
@utils.SITE_REPOSITORY_ARGUMENT
def generate_pki(site_name, author, days, regenerate_all, save_location):
    """Generate certificates, certificate authorities and keypairs for a given
    site.

    """
    output_paths = pegleg_main.run_generate_pki(
        author, days, regenerate_all, site_name, save_location)
    click.echo("Generated PKI files written to:\n%s" % '\n'.join(output_paths))


@generate.command('passphrases', help='Command to generate site passphrases')
@utils.SITE_REPOSITORY_ARGUMENT
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
@click.option(
    '-c',
    '--passphrase-catalog',
    'passphrase_catalog',
    required=False,
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help='Path to a specific passphrase catalog to generate passphrases from. '
    'If not specified, defaults to use catalogs discovered in the '
    'repositories.')
@click.option(
    '-i',
    '--interactive',
    'interactive',
    is_flag=True,
    default=False,
    help='Enables input prompts for "prompt: true" passphrases')
@click.option(
    '--force-cleartext',
    'force_cleartext',
    is_flag=True,
    default=False,
    show_default=True,
    help='Force cleartext generation of passphrases. This is not recommended.')
def generate_passphrases(
        *, site_name, save_location, author, passphrase_catalog, interactive,
        force_cleartext):
    pegleg_main.run_generate_passphrases(
        author, force_cleartext, interactive, save_location, site_name,
        passphrase_catalog)


@secrets.command(
    'encrypt',
    help='Command to encrypt and wrap site secrets '
    'documents with metadata.storagePolicy set '
    'to encrypted, in pegleg managed documents.')
@click.option(
    '-p',
    '--path',
    'path',
    type=click.Path(exists=True, readable=True),
    required=False,
    help='The file or directory path to encrypt. '
    'If path is not provided, all applicable files for the site '
    'will be encrypted.')
@click.option(
    '-s',
    '--save-location',
    'save_location',
    required=True,
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
@utils.SITE_REPOSITORY_ARGUMENT
def encrypt(*, path, save_location, author, site_name):
    pegleg_main.run_encrypt(author, save_location, site_name, path=path)


@secrets.command(
    'decrypt',
    help='Command to unwrap and decrypt one site '
    'secrets document and print it to stdout.')
@click.option(
    '--path',
    'path',
    type=click.Path(exists=True, readable=True),
    required=True,
    multiple=True,
    help='The file or directory path to decrypt. Multiple entries allowed.')
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
@utils.SITE_REPOSITORY_ARGUMENT
def decrypt(*, path, save_location, overwrite, site_name):
    data = pegleg_main.run_decrypt(overwrite, path, save_location, site_name)
    if data:
        for d in data:
            click.echo(d)


@main.group(help='Miscellaneous generate commands')
def generate():
    pass


@generate.command(
    'passphrase',
    help='Command to generate a passphrase and print out to stdout')
@click.option(
    '-l',
    '--length',
    'length',
    default=24,
    show_default=True,
    help='Generate a passphrase of the given length. '
    'Length is >= 24, no maximum length.')
def generate_passphrase(length):
    click.echo(
        'Generated Passhprase: {}'.format(
            pegleg_main.run_generate_passphrase(length)))


@generate.command(
    'salt', help='Command to generate a salt and print out to stdout')
@click.option(
    '-l',
    '--length',
    'length',
    default=24,
    show_default=True,
    help='Generate a salt of the given length. '
    'Length is >= 24, no maximum length.')
def generate_salt(length):
    click.echo(
        "Generated Salt: {}".format(pegleg_main.run_generate_salt(length)))

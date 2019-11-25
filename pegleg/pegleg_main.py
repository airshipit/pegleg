# Copyright 2019. AT&T Intellectual Property.  All other rights reserved.
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

from pegleg import config
from pegleg import engine
from pegleg.engine import bundle
from pegleg.engine import catalog
from pegleg.engine.secrets import wrap_secret
from pegleg.engine.util import files
from pegleg.engine.util.shipyard_helper import ShipyardHelper

LOG_FORMAT = '%(asctime)s %(levelname)-8s %(name)s:' \
             '%(funcName)s [%(lineno)3d] %(message)s'  # noqa

LOG = logging.getLogger(__name__)


def set_logging_level(verbose=False, logging_level=40):
    """Sets logging level used for pegleg

    :param verbose: sets level to DEBUG when True
    :param logging_level: specifies logging level by numbers
    :return:
    """
    lvl = logging_level
    if verbose:
        lvl = logging.DEBUG
    logging.basicConfig(format=LOG_FORMAT, level=int(lvl))


def run_config(
        site_repository,
        clone_path,
        repo_key,
        repo_username,
        extra_repositories,
        run_umask=True,
        decrypt_repos=True):
    """Initializes pegleg configuration data

    :param site_repository: path or URL for site repository
    :param clone_path: directory in which to clone the site_repository
    :param repo_key: key for remote repository URL if needed
    :param repo_username: username to replace REPO_USERNAME in repository URL
                          if needed
    :param extra_repositories: list of extra repositories to read in documents
                               from, specified as "type=REPO_URL/PATH"
    :param run_umask: if True, runs set_umask for os file output
    :param decrypt_repos: if True, decrypts repos before executing command
    :return:
    """
    config.set_site_repo(site_repository)
    config.set_clone_path(clone_path)
    if extra_repositories:
        config.set_extra_repo_overrides(extra_repositories)
    config.set_repo_key(repo_key)
    config.set_repo_username(repo_username)
    if run_umask:
        config.set_umask()
    config.set_decrypt_repos(decrypt_repos)


def _run_lint_helper(
        *, fail_on_missing_sub_src, exclude_lint, warn_lint, site_name=None):
    """Helper for executing lint on specific site or all sites in repo."""
    if site_name:
        func = functools.partial(engine.lint.site, site_name=site_name)
    else:
        func = engine.lint.full
    warns = func(
        fail_on_missing_sub_src=fail_on_missing_sub_src,
        exclude_lint=exclude_lint,
        warn_lint=warn_lint)
    return warns


def _run_precommand_decrypt(site_name):
    if config.get_decrypt_repos():
        LOG.info('Executing pre-command repository decryption...')
        repo_list = config.all_repos()
        for repo in repo_list:
            secrets_path = os.path.join(
                repo.rstrip(os.path.sep), 'site', site_name, 'secrets')
            if os.path.exists(secrets_path):
                LOG.info('Decrypting %s', secrets_path)
                run_decrypt(True, secrets_path, None, site_name)
    else:
        LOG.debug('Skipping pre-command repository decryption.')


def run_lint(exclude_lint, fail_on_missing_sub_src, warn_lint):
    """Runs linting on a repository

    :param exclude_lint: exclude specified linting rules
    :param fail_on_missing_sub_src: if True, fails when a substitution source
                                    file is missing
    :param warn_lint: output warnings for specified rules
    :return: warnings developed from linting
    :rtype: list
    """
    engine.repository.process_site_repository(update_config=True)
    warns = _run_lint_helper(
        fail_on_missing_sub_src=fail_on_missing_sub_src,
        exclude_lint=exclude_lint,
        warn_lint=warn_lint)
    return warns


def run_collect(exclude_lint, save_location, site_name, validate, warn_lint):
    """Runs document collection to produce single file definitions, containing
    all information and documents required by airship

    :param exclude_lint: exclude specified linting rules
    :param save_location: path to output definition files to, ouputs to stdout
                          if None
    :param site_name: site name to collect from repository
    :param validate: validate documents prior to collection
    :param warn_lint: output warnings for specified rules
    :return:
    """
    _run_precommand_decrypt(site_name)
    if validate:
        # Lint the primary repo prior to document collection.
        _run_lint_helper(
            site_name=site_name,
            fail_on_missing_sub_src=True,
            exclude_lint=exclude_lint,
            warn_lint=warn_lint)
    engine.site.collect(site_name, save_location)


def run_list_sites(output_stream):
    """Output list of known sites in repository

    :param output_stream: where to output site list
    :return:
    """
    engine.repository.process_site_repository(update_config=True)
    engine.site.list_(output_stream)


def run_show(output_stream, site_name):
    """Shows details for one site

    :param output_stream: where to output site information
    :param site_name: site name to process
    :return:
    """
    engine.site.show(site_name, output_stream)


def run_render(output_stream, site_name, validate):
    """Render a site through the deckhand engine

    :param output_stream: where to output rendered site data
    :param site_name: site name to process
    :param validate: if True, validate documents using schema validation
    :return:
    """
    _run_precommand_decrypt(site_name)
    engine.site.render(site_name, output_stream, validate)


def run_lint_site(exclude_lint, fail_on_missing_sub_src, site_name, warn_lint):
    """Lints a specified site

    :param exclude_lint: exclude specified linting rules
    :param fail_on_missing_sub_src: if True, fails when a substitution source
                                    file is missing
    :param site_name: site name to collect from repository
    :param warn_lint: output warnings for specified rules
    :return:
    """
    _run_precommand_decrypt(site_name)
    return _run_lint_helper(
        fail_on_missing_sub_src=fail_on_missing_sub_src,
        exclude_lint=exclude_lint,
        warn_lint=warn_lint,
        site_name=site_name)


def run_upload(
        buffer_mode, collection, context_marker, ctx, os_auth_token,
        os_auth_url, os_domain_name, os_password, os_project_domain_name,
        os_project_name, os_user_domain_name, os_username, site_name):
    """Uploads a collection of documents to shipyard

    :param buffer_mode: mode used when uploading documents
    :param collection: specifies the name to use for uploaded collection
    :param context_marker: UUID used to correlate logs, transactions, etc...
    :param ctx: dictionary containing various data used by shipyard
    :param os_auth_token: authentication token
    :param os_auth_url: authentication url
    :param os_domain_name: domain name
    :param os_password: password
    :param os_project_domain_name: project domain name
    :param os_project_name: project name
    :param os_user_domain_name: user domain name
    :param os_username: username
    :param site_name: site name to process
    :return: response from shipyard instance
    """
    _run_precommand_decrypt(site_name)
    if not ctx.obj:
        ctx.obj = {}
    # Build API parameters required by Shipyard API Client.
    if os_auth_token:
        os.environ['OS_AUTH_TOKEN'] = os_auth_token
        auth_vars = {'token': os_auth_token, 'auth_url': os_auth_url}
    else:
        auth_vars = {
            'user_domain_name': os_user_domain_name,
            'project_name': os_project_name,
            'username': os_username,
            'password': os_password,
            'auth_url': os_auth_url
        }
    # Domain-scoped params
    if os_domain_name:
        auth_vars['domain_name'] = os_domain_name
        auth_vars['project_domain_name'] = None
    # Project-scoped params
    else:
        auth_vars['project_domain_name'] = os_project_domain_name
    ctx.obj['API_PARAMETERS'] = {'auth_vars': auth_vars}
    ctx.obj['context_marker'] = str(context_marker)
    ctx.obj['site_name'] = site_name
    ctx.obj['collection'] = collection
    config.set_global_enc_keys(site_name)
    return ShipyardHelper(ctx, buffer_mode).upload_documents()


def run_generate_pki(
        author, days, regenerate_all, site_name, save_location=None):
    """Generates certificates from PKI catalog

    :param author: identifies author generating new certificates for
                   tracking information
    :param days: duration in days for the certificate to be valid
    :param regenerate_all: force regeneration of all certs, regardless of
                           expiration
    :param site_name: site name to process
    :param save_location: directory to store the generated site certificates in
    :return: list of paths written to
    """
    _run_precommand_decrypt(site_name)
    engine.repository.process_repositories(site_name, overwrite_existing=True)
    pkigenerator = catalog.pki_generator.PKIGenerator(
        site_name,
        author=author,
        duration=days,
        regenerate_all=regenerate_all,
        save_location=save_location)
    output_paths = pkigenerator.generate()
    return output_paths


def run_wrap_secret(
        author, encrypt, filename, layer, name, output_path, schema,
        site_name):
    """Wraps a bare secrets file with identifying information for pegleg

    :param author: identifies author generating new certificates for
                   tracking information
    :param encrypt: if False, leaves files in cleartext format
    :param filename: path to file to be wrapped
    :param layer: layer for document to be wrapped in, e.g. site or global
    :param name: name for the docuemnt wrap
    :param output_path: path to output wrapped document to
    :param schema: schema for the document wrap
    :param site_name: site name to process
    :return:
    """
    config.set_global_enc_keys(site_name)
    wrap_secret(
        author,
        filename,
        output_path,
        schema,
        name,
        layer,
        encrypt,
        site_name=site_name)


def run_genesis_bundle(build_dir, site_name, validators):
    """Runs genesis bundle via promenade

    :param build_dir: output directory for the generated bundle
    :param site_name: site name to process
    :param validators: if True, runs validation scripts on genesis bundle
    :return:
    """
    _run_precommand_decrypt(site_name)
    encryption_key = os.environ.get("PROMENADE_ENCRYPTION_KEY")
    config.set_global_enc_keys(site_name)
    bundle.build_genesis(
        build_dir, encryption_key, validators,
        logging.DEBUG == LOG.getEffectiveLevel(), site_name)


def run_check_pki_certs(days, site_name):
    """Checks PKI certificates for upcoming expiration

    :param days: number of days in advance to check for upcoming expirations
    :param site_name: site name to process
    :return:
    """
    _run_precommand_decrypt(site_name)
    config.set_global_enc_keys(site_name)
    expiring_certs_exist, cert_results = engine.secrets.check_cert_expiry(
        site_name, duration=days)
    return expiring_certs_exist, cert_results


def run_list_types(output_stream):
    """List type names for a repository

    :param output_stream: stream to output list
    :return:
    """
    engine.repository.process_site_repository(update_config=True)
    engine.type.list_types(output_stream)


def run_generate_passphrases(
        author,
        force_cleartext,
        interactive,
        save_location,
        site_name,
        passphrase_catalog=None):
    """Generates passphrases for site

    :param author: identifies author generating new certificates for
                   tracking information
    :param force_cleartext: if True, forces cleartext output of passphrases
    :param interactive: Enables input prompts for "prompt: true" passphrases
    :param save_location: path to save generated passphrases to
    :param site_name: site name to process
    :param passphrase_catalog: path to a passphrase catalog to override other
    discovered catalogs
    :return:
    """
    _run_precommand_decrypt(site_name)
    config.set_global_enc_keys(site_name)
    engine.secrets.generate_passphrases(
        site_name,
        save_location,
        author,
        passphrase_catalog=passphrase_catalog,
        interactive=interactive,
        force_cleartext=force_cleartext)


def run_encrypt(author, save_location, site_name):
    """Wraps and encrypts site secret documents

    :param author: identifies author generating new certificates for
                   tracking information
    :param save_location: path to save encrypted documents to, if None the
                          original documents are overwritten
    :param site_name: site name to process
    :return:
    """
    config.set_global_enc_keys(site_name)
    if save_location is None:
        save_location = config.get_site_repo()
    engine.secrets.encrypt(save_location, author, site_name=site_name)


def run_decrypt(overwrite, path, save_location, site_name):
    """Unwraps and decrypts secret documents for a site

    :param overwrite: if True, overwrites original files with decrypted
    :param path: file or directory to decrypt
    :param save_location: if specified saves to the given path, otherwise
                          returns list of decrypted information
    :param site_name: site name to process
    :return: decrypted data list if save_location is None
    :rtype: list
    """
    decrypted_data = []
    config.set_global_enc_keys(site_name)
    decrypted = engine.secrets.decrypt(path, site_name=site_name)
    if overwrite:
        for path, data in decrypted.items():
            files.write(data, path)
    elif save_location is None:
        for data in decrypted.values():
            decrypted_data.append(data)
    else:
        for path, data in decrypted.items():
            file_name = os.path.split(path)[1]
            file_save_location = os.path.join(save_location, file_name)
            files.write(data, file_save_location)
    return decrypted_data


def run_generate_passphrase(length=24):
    """Generates a single passphrase

    :param length: length of passphrase
    :return: generated passphrase
    :rtype: str
    """
    return engine.secrets.generate_crypto_string(length)


def run_generate_salt(length=24):
    """Generates a single salt

    :param length: length of salt
    :return: generated salt
    :rtype: str
    """
    return engine.secrets.generate_crypto_string(length)

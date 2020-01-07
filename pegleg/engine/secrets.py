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

from collections import OrderedDict
from glob import glob
import logging
import os
import re

from prettytable import PrettyTable
import yaml

from pegleg import config
from pegleg.engine.catalog.pki_utility import PKIUtility
from pegleg.engine import exceptions
from pegleg.engine.generators.passphrase_generator import PassphraseGenerator
from pegleg.engine.util.cryptostring import CryptoString
from pegleg.engine.util import definition
from pegleg.engine.util import encryption
from pegleg.engine.util import files
from pegleg.engine.util.pegleg_managed_document import \
    PeglegManagedSecretsDocument as PeglegManagedSecret
from pegleg.engine.util.pegleg_secret_management import PeglegSecretManagement

__all__ = ('encrypt', 'decrypt', 'generate_passphrases', 'wrap_secret')

LOG = logging.getLogger(__name__)


def encrypt(save_location, author, site_name, path=None):
    """
    Encrypt all secrets documents for a site identifies by site_name.

    Parse through all documents related to ``site_name`` and encrypt all
    site documents, which have metadata.storagePolicy: encrypted, and
    are not already encrypted and wrapped in a PeglegManagedDocument.
    ``Passphrase`` and ``salt`` for the encryption are read from environment
    variables``$PEGLEG_PASSPHRASE`` and ``$PEGLEG_SALT`` respectively.
    By default, the resulting output files will overwrite the original
    unencrypted secrets documents.

    :param str save_location: if provided, is used as the base directory to
    store the encrypted secrets files. If not provided, the encrypted
    secrets files will overwrite the original unencrypted files (default
    behavior).
    :param str author: Identifies the individual or application, who
    encrypts the secrets documents.
    :param str site_name: The name of the site to encrypt its secrets files.
    :param str path: The path to the directory or file to be encrypted.
    """

    files.check_file_save_location(save_location)
    LOG.debug('Save location is %s', save_location)

    file_sets = []
    path_exists = path and os.path.exists(path)
    if path_exists:
        if os.path.isfile(path):
            LOG.debug('Specified path is a file')
            file_sets = [(None, path)]
        elif os.path.isdir(path):
            LOG.debug('Specified path is a directory')
            file_sets = []
            for filename in glob(os.path.join(path, '**/*.yaml'),
                                 recursive=True):
                LOG.debug('Discovered %s', filename)
                file_sets.append((None, filename))
    else:
        LOG.debug('No path specified, searching all repos')
        file_sets = list(definition.site_files_by_repo(site_name))

    LOG.info('Started encrypting...')
    secrets_found = False
    for repo_base, file_path in file_sets:
        LOG.debug('Looking at %s in %s repo', file_path, repo_base)
        secrets_found = True
        secret = PeglegSecretManagement(
            file_path=file_path, author=author, site_name=site_name)
        if path_exists:
            if save_location:
                output_path = os.path.join(
                    save_location.rstrip(os.path.sep),
                    file_path.lstrip(os.path.sep))
            else:
                output_path = file_path
        else:
            output_path = _get_dest_path(repo_base, file_path, save_location)
        LOG.debug('Outputting encrypted data to %s', output_path)
        secret.encrypt_secrets(output_path)

    if secrets_found:
        LOG.info('Encryption of all secret files was completed.')
    else:
        LOG.warning(
            'No secret documents were found for site: {}'.format(site_name))


def decrypt(path, site_name=None):
    """Decrypt one secrets file, and print the decrypted file to standard out.

    Search the specified file_path for a file.
    If the file is found and encrypted, unwrap and decrypt it, and print the
    result to standard out.
    If the file is found, but it is not encrypted, print the contents of the
    file to standard out.
    Passphrase and salt for the decryption are read from environment variables.
    :param path: Path to the file to be unwrapped and decrypted.
    :type path: string
    :return: The decrypted secrets
    :rtype: dict
    """
    LOG.info('Started decrypting...')
    file_dict = {}

    if not os.path.exists(path):
        LOG.error(
            'Path: {} was not found. Check your path and site name, '
            'and try again.'.format(path))
        return file_dict

    if os.path.isfile(path):
        file_dict[path] = PeglegSecretManagement(
            path, site_name=site_name).decrypt_secrets()
    else:
        match = os.path.join(path, '**', '*.yaml')
        file_list = glob(match, recursive=True)
        if not file_list:
            LOG.warning(
                'No YAML files were discovered in path: {}'.format(path))
        for file_path in file_list:
            file_dict[file_path] = PeglegSecretManagement(
                file_path).decrypt_secrets()
    return file_dict


def _get_dest_path(repo_base, file_path, save_location):
    """
    Calculate and return the destination base directory path for the
    encrypted secrets files.

    :param repo_base: Base repo of the source secrets file.
    :type repo_base: string
    :param file_path: File path to the source secrets file.
    :type file_path: string
    :param save_location: Base location of destination secrets file
    :type save_location: string
    :return: The file path of the destination secrets file.
    :rtype: string
    """

    if (save_location and save_location != os.path.sep
            and save_location.endswith(os.path.sep)):
        save_location = save_location.rstrip(os.path.sep)
    if repo_base and repo_base.endswith(os.path.sep):
        repo_base = repo_base.rstrip(os.path.sep)
    if save_location:
        return file_path.replace(repo_base, save_location)
    else:
        return file_path


def generate_passphrases(
        site_name,
        save_location,
        author,
        passphrase_catalog=None,
        interactive=False,
        force_cleartext=False):
    """
    Look for the site passphrase catalogs, and for every passphrase entry in
    the passphrase catalog generate a passphrase document, wrap the
    passphrase document in a pegleg managed document, and encrypt the
    passphrase data.

    :param str site_name: The site to read from
    :param str save_location: Location to write files to
    :param str author: Author who's generating the files
    :param path-like passphrase_catalog: Path to file overriding any other
    discovered passphrase catalogs
    :param bool interactive: Whether to allow user input for passphrases
    :param bool force_cleartext: Whether to generate results in clear text
    """
    override_passphrase_catalog = passphrase_catalog
    if passphrase_catalog:
        override_passphrase_catalog = files.read(passphrase_catalog)

    PassphraseGenerator(
        site_name, save_location, author,
        override_passphrase_catalog).generate(
            interactive=interactive, force_cleartext=force_cleartext)


def generate_crypto_string(length):
    """
    Create a cryptographic string.

    :param int length: Length of cryptographic string.
    :rtype: string
    """

    return CryptoString().get_crypto_string(length)


def wrap_secret(
        author,
        filename,
        output_path,
        schema,
        name,
        layer,
        encrypt,
        site_name=None):
    """Wrap a bare secrets file in a YAML and ManagedDocument.

    :param author: author for ManagedDocument
    :param filename: file path for input file
    :param output_path: file path for output file
    :param schema: schema for wrapped document
    :param name: name for wrapped document
    :param layer: layer for wrapped document
    :param encrypt: whether to encrypt the output doc
    """

    if not output_path:
        output_path = os.path.splitext(filename)[0] + ".yaml"

    with open(filename, 'r') as in_fi:
        data = in_fi.read()

    inner_doc = OrderedDict(
        [
            ("schema", schema), ("data", data),
            (
                "metadata",
                OrderedDict(
                    [
                        (
                            "layeringDefinition",
                            OrderedDict(
                                [("abstract", False), ("layer", layer)])),
                        ("name", name), ("schema", "metadata/Document/v1"),
                        (
                            "storagePolicy",
                            "encrypted" if encrypt else "cleartext")
                    ]))
        ])
    managed_secret = PeglegManagedSecret(inner_doc, author=author)
    if encrypt:
        psm = PeglegSecretManagement(
            docs=[inner_doc], author=author, site_name=site_name)
        output_doc = psm.get_encrypted_secrets()[0][0]
    else:
        output_doc = managed_secret.pegleg_document
    files.safe_dump(output_doc, output_path, sort_keys=False)


def check_cert_expiry(site_name, duration=60):
    """
    Check certs from a sites PKICatalog to determine if they are expired or
    expiring within N days

    :param str site_name: The site to read from
    :param int duration: Number of days from today to check cert
        expirations
    :rtype: str
    """

    cert_schemas = [
        'deckhand/Certificate/v1', 'deckhand/CertificateAuthority/v1'
    ]
    pki_util = PKIUtility(duration=duration)
    # Create a table to output expired/expiring certs for this site.
    cert_table = PrettyTable()
    cert_table.field_names = ['file', 'cert_name', 'expiration_date']
    expired_certs_exist = False

    s = definition.site_files(site_name)
    for doc in s:
        if 'certificate' in doc:
            with open(doc, 'r') as f:
                results = yaml.safe_load_all(f)  # Validate valid YAML.
                results = PeglegSecretManagement(
                    docs=results).get_decrypted_secrets()
                for result in results:
                    if result['schema'] in cert_schemas:
                        text = result['data']
                        header_pattern = '-----BEGIN CERTIFICATE-----'
                        find_pattern = r'%s.*?(?=%s|$)' % (
                            header_pattern, header_pattern)
                        certs = re.findall(find_pattern, text, re.DOTALL)
                        for cert in certs:
                            cert_info = pki_util.check_expiry(cert)
                            if cert_info['expired'] is True:
                                cert_table.add_row(
                                    [
                                        doc, result['metadata']['name'],
                                        cert_info['expiry_date']
                                    ])
                                expired_certs_exist = True

    # Return table of cert names and expiration dates that are expiring
    return expired_certs_exist, cert_table.get_string()


def get_global_creds(site_name):
    """Determine which credentials to use for global secrets.

    If a user desires to encrypt site secrets with one set of credentials but
    global secrets with a different set of credentials (in the case of
    multiple sites) Pegleg needs a way to handle a two-step encryption or
    decryption chain. This is accomplished by storing global credentials at
    the site level and encrypting them with site credentials. Pegleg will
    attempt to find both the global_salt and global_passphrase, decrypt them
    then use these credentials for any global encrypt/decrypt operations.
    If both global_salt and global_passphrase are found return both.
    If only one global credential is found, raise an error with the assumption
    the user wishes to use global credentials but does not have both.
    If neither are found, return the site credentials with the assumption
    the user wishes to encrypt the global documents with the site credentials.

    :param str site_name: The target site
    :return: Either the global, or site level - passphrase and salt
    """

    config.set_passphrase()
    config.set_salt()
    global_passphrase = None
    global_salt = None
    docs = definition.documents_for_site(site_name)

    for doc in docs:
        if doc['schema'] == 'pegleg/PeglegManagedDocument/v1':
            try:
                name = doc['data']['managedDocument']['metadata']['name']
                schema = doc['data']['managedDocument']['schema']
                data = doc['data']['managedDocument']['data']
                if schema == 'deckhand/Passphrase/v1':
                    if name == 'global_passphrase':
                        global_passphrase = encryption.decrypt(
                            data, config.get_passphrase(), config.get_salt())
                    elif name == 'global_salt':
                        global_salt = encryption.decrypt(
                            data, config.get_passphrase(), config.get_salt())
            except KeyError:
                continue
        else:
            try:
                name = doc['metadata']['name']
                schema = doc['schema']
                data = doc['data']
                if name == 'global_passphrase':
                    global_passphrase = data.encode()
                elif name == 'global_salt':
                    global_salt = data.encode()
            except KeyError:
                continue
        # Break out of search if both passphrase and salt are found
        if global_passphrase and global_salt:
            return (global_passphrase, global_salt)

    # End of search, determine if we should use site keys or raise an error
    if global_passphrase or global_salt:
        raise exceptions.GlobalCredentialsNotFound()
    else:
        return (config.get_passphrase(), config.get_salt())

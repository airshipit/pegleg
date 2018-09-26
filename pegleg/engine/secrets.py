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

from pegleg.engine.generators.passpharase_generator import PassphraseGenerator
from pegleg.engine.util import definition
from pegleg.engine.util import files
from pegleg.engine.util.pegleg_secret_management import PeglegSecretManagement

__all__ = ('encrypt', 'decrypt', 'generate_passphrases')

LOG = logging.getLogger(__name__)


def encrypt(save_location, author, site_name):
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
    """

    files.check_file_save_location(save_location)
    LOG.info('Started encrypting...')
    secrets_found = False
    for repo_base, file_path in definition.site_files_by_repo(site_name):
        secrets_found = True
        PeglegSecretManagement(
            file_path=file_path, author=author).encrypt_secrets(
            _get_dest_path(repo_base, file_path, save_location))
    if secrets_found:
        LOG.info('Encryption of all secret files was completed.')
    else:
        LOG.warn(
            'No secret documents were found for site: {}'.format(site_name))


def decrypt(file_path, site_name):
    """
    Decrypt one secrets file, and print the decrypted file to standard out.

    Search in secrets file of a site, identified by ``site_name``, for a file
    named ``file_name``.
    If the  file is found and encrypted, unwrap and decrypt it, and print the
    result to standard out.
    If the file is found, but it is not encrypted, print the contents of the
    file to standard out.
    Passphrase and salt for the decryption are read from environment variables.
    :param file_path: Path to the file to be unwrapped and decrypted.
    :type file_path: string
    :param site_name: The name of the site to search for the file.
    :type site_name: string
    :return: The decrypted secrets
    :rtype: list
    """
    LOG.info('Started decrypting...')
    if (os.path.isfile(file_path) and
            [s for s in file_path.split(os.path.sep) if s == site_name]):
        return PeglegSecretManagement(file_path).decrypt_secrets()
    else:
        LOG.info('File: {} was not found. Check your file path and name, '
                 'and try again.'.format(file_path))


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

    if (save_location and save_location != os.path.sep and
            save_location.endswith(os.path.sep)):
        save_location = save_location.rstrip(os.path.sep)
    if repo_base and repo_base.endswith(os.path.sep):
        repo_base = repo_base.rstrip(os.path.sep)
    if save_location:
        return file_path.replace(repo_base, save_location)
    else:
        return file_path


def generate_passphrases(site_name, save_location, author, interactive=False):
    """
    Look for the site passphrase catalogs, and for every passphrase entry in
    the passphrase catalog generate a passphrase document, wrap the
    passphrase document in a pegleg managed document, and encrypt the
    passphrase data.

    :param interactive: Whether to generate the results interactively
    :param str site_name: The site to read from
    :param str save_location: Location to write files to
    :param str author:
    """

    PassphraseGenerator(site_name, save_location, author).generate(
        interactive=interactive)

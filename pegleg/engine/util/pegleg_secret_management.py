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
import yaml
import sys
import re
import click

from pegleg.engine.util.encryption import encrypt
from pegleg.engine.util.encryption import decrypt
from pegleg.engine.util.pegleg_managed_document import \
    PeglegManagedSecretsDocument as PeglegManagedSecret
from pegleg.engine.util import files

LOG = logging.getLogger(__name__)
PASSPHRASE_PATTERN = '^.{24,}$'
ENV_PASSPHRASE = 'PEGLEG_PASSPHRASE'
ENV_SALT = 'PEGLEG_SALT'


class PeglegSecretManagement():
    """An object to handle operations on of a pegleg managed file."""

    def __init__(self, file_path):
        """
        Read the source file and the environment data needed to wrap and
        process the file documents as pegleg managed document.
        """

        self.__check_environment()
        self.file_path = file_path
        self.documents = list()
        for doc in files.read(file_path):
            self.documents.append(PeglegManagedSecret(doc))

        self.passphrase = os.environ.get(ENV_PASSPHRASE).encode()
        self.salt = os.environ.get(ENV_SALT).encode()

    @staticmethod
    def __check_environment():
        """
        Validate required environment variables for encryption or decryption.

        :return None
        :raises click.ClickException: If environment validation should fail.
        """

        # Verify that passphrase environment variable is defined and is longer
        # than 24 characters.
        if not os.environ.get(ENV_PASSPHRASE) or not re.match(
            PASSPHRASE_PATTERN, os.environ.get(ENV_PASSPHRASE)):
            raise click.ClickException(
                'Environment variable {} is not defined or '
                'is not at least 24-character long.'.format(ENV_PASSPHRASE))

        if not os.environ.get(ENV_SALT):
            raise click.ClickException(
                'Environment variable {} is not defined or '
                'is an empty string.'.format(ENV_SALT))

    def encrypt_secrets(self, save_path, author):
        """
        Wrap and encrypt the secrets documents included in the input file,
        into pegleg manage secrets documents, and write the result in
        save_path.

        if save_path is the same as the source file_path the encrypted file
        will overwrite the source file.

        :param save_path: Destination path of the encrypted file
        :type save_path: string
        :param author: Identifier for the program or person who is
        encrypting the secrets documents
        :type author: string
        """

        encrypted_docs = False
        doc_list = []
        for doc in self.documents:
            # do not re-encrypt already encrypted data
            if doc.is_encrypted():
                continue

            # only encrypt if storagePolicy is set to encrypted.
            if not doc.is_storage_policy_encrypted():
                # case documents in a file have different storage
                # policies
                doc_list.append(doc.embedded_document)
                continue

            doc.set_secret(
                encrypt(doc.get_secret().encode(), self.passphrase, self.salt))
            doc.set_encrypted(author)
            encrypted_docs = True
            doc_list.append(doc.pegleg_document)
        if encrypted_docs:
            files.write(save_path, doc_list)
            LOG.info('Wrote data to: {}.'.format(save_path))
        else:
            LOG.debug('All documents in file: {} are either already encrypted '
                      'or have cleartext storage policy. '
                      'Skipping.'.format(self.file_path))

    def decrypt_secrets(self):
        """Decrypt and unwrap pegleg managed encrypted secrets documents
        included in a site secrets file, and print the result to the standard
        out."""

        doc_list = []
        for doc in self.documents:
            # only decrypt an encrypted document
            if doc.is_encrypted():
                doc.set_secret(
                    decrypt(doc.get_secret(),
                            self.passphrase,
                            self.salt).decode())
                doc.set_decrypted()
            doc_list.append(doc.embedded_document)
        yaml.safe_dump_all(
            doc_list,
            sys.stdout,
            explicit_start=True,
            explicit_end=True,
            default_flow_style=False)

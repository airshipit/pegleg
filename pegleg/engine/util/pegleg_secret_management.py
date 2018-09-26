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
import re

import click
import yaml

from pegleg.engine.util.encryption import decrypt
from pegleg.engine.util.encryption import encrypt
from pegleg.engine.util import files
from pegleg.engine.util.pegleg_managed_document import \
    PeglegManagedSecretsDocument as PeglegManagedSecret

LOG = logging.getLogger(__name__)
PASSPHRASE_PATTERN = '^.{24,}$'
ENV_PASSPHRASE = 'PEGLEG_PASSPHRASE'
ENV_SALT = 'PEGLEG_SALT'


class PeglegSecretManagement(object):
    """An object to handle operations on of a pegleg managed file."""

    def __init__(self, file_path=None, docs=None, generated=False,
                 catalog=None, author=None):
        """
        Read the source file and the environment data needed to wrap and
        process the file documents as pegleg managed document.
        Either of the ``file_path`` or ``docs`` must be
        provided.
        """

        if all([file_path, docs]) or not any([file_path, docs]):
            raise ValueError('Either `file_path` or `docs` must be '
                             'specified.')

        if generated and not (author and catalog):
            raise ValueError("If the document is generated, author and "
                             "catalog must be specified.")
        self.__check_environment()
        self.file_path = file_path
        self.documents = list()
        self._generated = generated

        if docs:
            for doc in docs:
                self.documents.append(PeglegManagedSecret(doc,
                                                          generated=generated,
                                                          catalog=catalog,
                                                          author=author))
        else:
            self.file_path = file_path
            for doc in files.read(file_path):
                self.documents.append(PeglegManagedSecret(doc))

        self._author = author

        self.passphrase = os.environ.get(ENV_PASSPHRASE).encode()
        self.salt = os.environ.get(ENV_SALT).encode()

    def __iter__(self):
        """
        Make the secret management object iterable
        :return: the wrapped documents
        """
        return (doc.pegleg_document for doc in self.documents)

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

    def encrypt_secrets(self, save_path):
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

        doc_list, encrypted_docs = self.get_encrypted_secrets()
        if encrypted_docs:
            files.write(save_path, doc_list)
            click.echo('Wrote encrypted data to: {}'.format(save_path))
        else:
            LOG.debug('All documents in file: {} are either already encrypted '
                      'or have cleartext storage policy. '
                      'Skipping.'.format(self.file_path))

    def get_encrypted_secrets(self):
        """
        :return doc_list: The list of documents
        :rtype doc_list: list
        :return encrypted_docs: Whether any documents were encrypted
        :rtype encrypted_docs: bool
        """
        if self._generated and not self._author:
            raise ValueError("An author is needed to encrypt "
                             "generated documents. "
                             "Specify it when PeglegSecretManagement "
                             "is initialized.")

        encrypted_docs = False
        doc_list = []
        for doc in self.documents:
            # do not re-encrypt already encrypted data
            if doc.is_encrypted():
                doc_list.append(doc)
                continue

            # only encrypt if storagePolicy is set to encrypted.
            if not doc.is_storage_policy_encrypted():
                # case documents in a file have different storage
                # policies
                doc_list.append(doc.embedded_document)
                continue

            doc.set_secret(
                encrypt(doc.get_secret().encode(), self.passphrase, self.salt))
            doc.set_encrypted(self._author)
            encrypted_docs = True
            doc_list.append(doc.pegleg_document)
        return doc_list, encrypted_docs

    def decrypt_secrets(self):
        """Decrypt and unwrap pegleg managed encrypted secrets documents
        included in a site secrets file, and print the result to the standard
        out."""

        secrets = self.get_decrypted_secrets()

        return yaml.safe_dump_all(
            secrets,
            explicit_start=True,
            explicit_end=True,
            default_flow_style=False)

    def get_decrypted_secrets(self):
        """
        Unwrap and decrypt all the pegleg managed documents in a secrets
        file, and return the result as a list of documents.

        The method is idempotent. If the method is called on not
        encrypted files, or documents inside the file, it will return
        the original unwrapped and unencrypted documents.

        """

        doc_list = []
        for doc in self.documents:
            # do not decrypt already decrypted data
            if doc.is_encrypted():
                doc.set_secret(
                    decrypt(doc.get_secret(), self.passphrase,
                            self.salt).decode())
                doc.set_decrypted()
            doc_list.append(doc.embedded_document)
        return doc_list

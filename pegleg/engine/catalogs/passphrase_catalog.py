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

from pegleg.engine.catalogs.base_catalog import BaseCatalog
from pegleg.engine.exceptions import PassphraseSchemaNotFoundException

LOG = logging.getLogger(__name__)
KIND = 'PassphraseCatalog'
P_DOCUMENT_NAME = 'document_name'
P_LENGTH = 'length'
P_DESCRIPTION = 'description'
P_ENCRYPTED = 'encrypted'
P_CLEARTEXT = 'cleartext'
P_DEFAULT_LENGTH = 24
P_DEFAULT_STORAGE_POLICY = 'encrypted'

__all__ = ['PassphraseCatalog']


class PassphraseCatalog(BaseCatalog):
    """Passphrase Catalog class.

    The object containing methods and attributes to ingest and manage the site
    passphrase catalog documents.

    """

    def __init__(self, sitename, documents=None):
        """
        Parse the site passphrase catalog documents and capture the
        passphrase catalog data.

        :param str sitename: Name of the environment
        :param list documents: Environment configuration documents
        :raises PassphraseSchemaNotFoundException: If it cannot find a
        ``pegleg/passphraseCatalog/v1`` document.
        """
        super(PassphraseCatalog, self).__init__(KIND, sitename, documents)
        if not self._catalog_docs:
            raise PassphraseSchemaNotFoundException()

    @property
    def get_passphrase_names(self):
        """Return the list of passphrases in the catalog."""
        return (passphrase[P_DOCUMENT_NAME]
                for catalog in self._catalog_docs
                for passphrase in catalog['data']['passphrases'])

    def get_length(self, passphrase_name):
        """
        Return the length of the ``passphrase_name``. If the catalog
        does not specify a length for the ``passphrase_name``, return the
        default passphrase length, 24.
        """

        for c_doc in self._catalog_docs:
            for passphrase in c_doc['data']['passphrases']:
                if passphrase[P_DOCUMENT_NAME] == passphrase_name:
                    return passphrase.get(P_LENGTH, P_DEFAULT_LENGTH)

    def get_storage_policy(self, passphrase_name):
        """
        Return the storage policy of the ``passphrase_name``.
        If the passphrase catalog does not specify a storage policy for
        this passphrase, return the default storage policy, "encrypted".
        """

        for c_doc in self._catalog_docs:
            for passphrase in c_doc['data']['passphrases']:
                if passphrase[P_DOCUMENT_NAME] == passphrase_name:
                    if P_ENCRYPTED in passphrase and not passphrase[
                            P_ENCRYPTED]:
                        return P_CLEARTEXT
                    else:
                        return P_DEFAULT_STORAGE_POLICY

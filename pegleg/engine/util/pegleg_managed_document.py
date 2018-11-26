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

from datetime import datetime
import logging

PEGLEG_MANAGED_SCHEMA = 'pegleg/PeglegManagedDocument/v1'
ENCRYPTED = 'encrypted'
STORAGE_POLICY = 'storagePolicy'
METADATA = 'metadata'
LOG = logging.getLogger(__name__)


class PeglegManagedSecretsDocument(object):
    """Object representing one Pegleg managed secret document."""

    def __init__(self, secrets_document):
        """
        Parse and wrap an externally generated document in a
        pegleg managed document.

        :param secrets_document: The content of the source document
        :type secrets_document: dict

        """

        if self.is_pegleg_managed_secret(secrets_document):
            self._pegleg_document = secrets_document
        else:
            self._pegleg_document =\
                self.__wrap(secrets_document)
        self._embedded_document = \
            self._pegleg_document['data']['managedDocument']

    @staticmethod
    def __wrap(secrets_document):
        """
        Embeds a valid deckhand document in a pegleg managed document.

        :param secrets_document: secrets document to be embedded in a
        pegleg managed document.
        :type secrets_document: dict
        :return: pegleg manged document with the wrapped original secrets
        document.
        :rtype: dict
        """

        return {
            'schema': PEGLEG_MANAGED_SCHEMA,
            'metadata': {
                'name': secrets_document['metadata']['name'],
                'schema': 'deckhand/Document/v1',
                'labels': secrets_document['metadata'].get('labels', {}),
                'layeringDefinition': {
                    'abstract': False,
                    # The current requirement only requires site layer.
                    'layer': 'site',
                },
                'storagePolicy': 'cleartext'
            },
            'data': {
                'managedDocument': {
                    'schema': secrets_document['schema'],
                    'metadata': secrets_document['metadata'],
                    'data': secrets_document['data']
                }
            }
        }

    @staticmethod
    def is_pegleg_managed_secret(secrets_document):
        """"
        Verify if the document is already a pegleg managed secrets document.

        :return: True if the document is a pegleg managed secrets document,
        False otherwise.
        :rtype: bool
        """
        return PEGLEG_MANAGED_SCHEMA in secrets_document.get('schema')

    @property
    def embedded_document(self):
        """
        parse the pegleg managed document, and return the embedded document

        :return: The original secrets document unwrapped from the pegleg
        managed document.
        :rtype: dict
        """
        return self._embedded_document

    @property
    def name(self):
        return self._pegleg_document.get('metadata', {}).get('name')

    @property
    def data(self):
        return self._pegleg_document.get('data')

    @property
    def pegleg_document(self):
        return self._pegleg_document

    def is_encrypted(self):
        """If the document is already encrypted return True. False
        otherwise."""
        return ENCRYPTED in self.data

    def is_storage_policy_encrypted(self):
        """If the document's storagePolicy is set to encrypted return True.
        False otherwise."""
        return STORAGE_POLICY in self._embedded_document[METADATA] \
            and ENCRYPTED in self._embedded_document[METADATA][STORAGE_POLICY]

    def set_encrypted(self, author):
        """Mark the pegleg managed document as encrypted."""
        self.data[ENCRYPTED] = {
            'at': datetime.utcnow().isoformat(),
            'by': author,
        }

    def set_decrypted(self):
        """Mark the pegleg managed document as un-encrypted."""
        self.data.pop(ENCRYPTED)

    def set_secret(self, secret):
        self._embedded_document['data'] = secret

    def get_secret(self):
        return self._embedded_document.get('data')

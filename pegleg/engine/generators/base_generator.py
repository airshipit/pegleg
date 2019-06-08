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

from abc import ABC
import logging
import os

from pegleg.engine import util

__all__ = ['BaseGenerator']

LOG = logging.getLogger(__name__)


class BaseGenerator(ABC):
    """
    Abstract Base Class, providing the common data and methods for all
    generator classes
    """

    def __init__(self, sitename, save_location, author=None):
        """Constructor for ``BaseGenerator``.

        :param str sitename: Name of the environment.
        :param str save_location: The destination directory to store the
        generated documents.
        :param str author: Identifier for the individual or the application,
        who requests to generate a document.
        """

        self._sitename = sitename
        self._documents = util.definition.documents_for_site(sitename)
        self._save_location = save_location
        self._author = author

    @staticmethod
    def generate_doc(kind, name, storage_policy, secret_data):
        """
        Generate a document of the specified ``kind``, with the
        specified ``storage_policy`` for the ``secret_data``.

        :param str kind: Kind of the secret document.
        :param str name: Name of the secret document
        :param str storage_policy: Storage policy for the secret data
        :param str secret_data: The data to be stored in this document.
        """
        return {
            'schema': 'deckhand/{}/v1'.format(kind),
            'metadata': {
                'schema': 'metadata/Document/v1',
                'name': name,
                'layeringDefinition': {
                    'abstract': False,
                    'layer': 'site',
                },
                'storagePolicy': storage_policy,
            },
            'data': secret_data,
        }

    def get_save_path(self, passphrase_name):
        """Calculate and return the save path of the ``passphrase_name``."""
        return os.path.abspath(
            os.path.join(
                self._save_location, 'site', self._sitename, 'secrets',
                self.kind_path, '{}.yaml'.format(passphrase_name)))

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
from pegleg.engine.catalogs import passphrase_profiles
from pegleg.engine import exceptions

LOG = logging.getLogger(__name__)
KIND = 'PassphraseCatalog'
P_DOCUMENT_NAME = 'document_name'
P_LENGTH = 'length'
P_DESCRIPTION = 'description'
P_ENCRYPTED = 'encrypted'
P_CLEARTEXT = 'cleartext'
P_TYPE = 'type'
P_REGENERABLE = 'regenerable'
P_PROMPT = 'prompt'
P_DEFAULT_LENGTH = 24
P_DEFAULT_STORAGE_POLICY = 'encrypted'
P_DEFAULT_TYPE = 'passphrase'
P_DEFAULT_REGENERABLE = True
P_DEFAULT_PROMPT = False
VALID_PASSPHRASE_TYPES = ['passphrase', 'base64', 'uuid']
VALID_BOOLEAN_FIELDS = [True, False]
P_PROFILE = 'profile'
P_DEFAULT_PROFILE = 'default'

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
        :raises PassphraseCatalogNotFoundException: If it cannot find a
        ``pegleg/passphraseCatalog/v1`` document.
        """
        super(PassphraseCatalog, self).__init__(KIND, sitename, documents)
        if not self._catalog_docs:
            raise exceptions.PassphraseCatalogNotFoundException()

    @property
    def get_passphrase_names(self):
        """Return the list of passphrases in the catalog."""
        return (
            passphrase[P_DOCUMENT_NAME] for catalog in self._catalog_docs
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

    def get_passphrase_type(self, passphrase_name):
        """Return the type of the ``passphrase_name``.

        Determine what type of secret this passphrase name is. Valid options:
        1. passphrase (a randomly generated passphrase)
        2. base64 (a randomly generated passphrase, encoded with base64)
        3. uuid (a randomly generated UUID)

        If an invalid option is specified, raise an exception. If a valid
        option is specified, return it. If no option is specified, default to
        passphrase.
        """

        for c_doc in self._catalog_docs:
            for passphrase in c_doc['data']['passphrases']:
                if passphrase[P_DOCUMENT_NAME] == passphrase_name:
                    passphrase_type = passphrase.get(P_TYPE,
                                                     P_DEFAULT_TYPE).lower()
                    if passphrase_type not in VALID_PASSPHRASE_TYPES:
                        raise exceptions.InvalidPassphraseType(
                            ptype=passphrase_type,
                            pname=passphrase_name,
                            validvalues=VALID_PASSPHRASE_TYPES)
                    else:
                        return passphrase_type

    def is_passphrase_regenerable(self, passphrase_name):
        """Return the regenerable field of the ``passphrase_name``.

        Determines if this passphrase name is regenerable.
        Valid options: True, False.
        If no option is specified, default to True. If an invalid option is
        specified, raise an exception

        """
        # UUIDs should not be regenerated
        if self.get_passphrase_type(passphrase_name) == 'uuid':
            return False

        # All other types can be regenerated
        for c_doc in self._catalog_docs:
            for passphrase in c_doc['data']['passphrases']:
                if passphrase[P_DOCUMENT_NAME] == passphrase_name:
                    passphrase_regenerable = passphrase.get(
                        P_REGENERABLE, P_DEFAULT_REGENERABLE)
                    if passphrase_regenerable not in VALID_BOOLEAN_FIELDS:
                        raise exceptions.InvalidPassphraseRegeneration(
                            pregen=passphrase_regenerable,
                            pname=passphrase_name,
                            validvalues=VALID_BOOLEAN_FIELDS)
                    else:
                        return passphrase_regenerable

    def is_passphrase_prompt(self, passphrase_name):
        """Return the prompt field of the ``passphrase_name``.

        Determines if this passphrase name should be generated interactively.
        Valid options: True, False.
        If no option is specified, default to False. If an invalid option is
        specified, raise an exception

        """

        for c_doc in self._catalog_docs:
            for passphrase in c_doc['data']['passphrases']:
                if passphrase[P_DOCUMENT_NAME] == passphrase_name:
                    passphrase_prompt = passphrase.get(
                        P_PROMPT, P_DEFAULT_PROMPT)
                    if passphrase_prompt not in VALID_BOOLEAN_FIELDS:
                        raise exceptions.InvalidPassphrasePrompt(
                            pprompt=passphrase_prompt,
                            pname=passphrase_name,
                            validvalues=VALID_BOOLEAN_FIELDS)
                    else:
                        return passphrase_prompt

    def get_passphrase_profile(self, passphrase_name):
        """Return the profile field of the ``passphrase_name``.

        Determine which profile this passphrase should use when selecting
        the pool to generate passphrase from.
        If no option is specified, use default profile.  See
        pegleg.engine.catalogs.passphrase_profiles for default and valid
        options.
        """

        for c_doc in self._catalog_docs:
            for passphrase in c_doc['data']['passphrases']:
                if passphrase[P_DOCUMENT_NAME] == passphrase_name:
                    profile = passphrase.get(P_PROFILE,
                                             P_DEFAULT_PROFILE).lower()
                    if profile not in passphrase_profiles.VALID_PROFILES:
                        raise exceptions.InvalidPassphraseProfile(
                            pprofile=profile,
                            validvalues=passphrase_profiles.VALID_PROFILES)
                    else:
                        return profile

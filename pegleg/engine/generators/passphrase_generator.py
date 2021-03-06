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

import base64
from getpass import getpass
import logging
import os
import re

import click
from oslo_utils import uuidutils

from pegleg.engine.catalogs import passphrase_catalog
from pegleg.engine.catalogs.passphrase_catalog import PassphraseCatalog
from pegleg.engine.generators.base_generator import BaseGenerator
from pegleg.engine.util.cryptostring import CryptoString
from pegleg.engine.util import files
from pegleg.engine.util.pegleg_secret_management import PeglegSecretManagement

__all__ = ['PassphraseGenerator']

LOG = logging.getLogger(__name__)
KIND = 'Passphrase'
KIND_PATH = 'passphrases'


class PassphraseGenerator(BaseGenerator):
    """
    Generates passphrases for a given environment, specified in a
    passphrase catalog.
    """
    def __init__(
            self,
            sitename,
            save_location,
            author,
            override_passphrase_catalog=None):
        """Constructor for ``PassphraseGenerator``.

        :param str sitename: Site name for which passphrases are generated.
        :param str save_location: The base directory to store the generated
        passphrase documents.
        :param str author: Identifying name of the author generating new
        certificates.
        """
        super(PassphraseGenerator,
              self).__init__(sitename, save_location, author)
        self._catalog = PassphraseCatalog(
            self._sitename,
            documents=override_passphrase_catalog or self._documents)

    def generate(self, interactive=False, force_cleartext=False):
        """
        For each passphrase entry in the passphrase catalog, generate a
        random passphrase string, based on a passphrase specification in the
        catalog. Create a pegleg managed document, wrap the generated
        passphrase document in the pegleg managed document, and encrypt the
        passphrase. Write the wrapped and encrypted document in a file at
        <repo_name>/site/<site_name>/secrets/passphrases/passphrase_name.yaml.

        :param bool interactive: If true, allow input
        :param bool force_cleartext: If true, don't encrypt
        """
        for p_name in self._catalog.get_passphrase_names:
            # Check if this secret is present and should not be regenerated
            save_path = self.get_save_path(p_name)
            regenerable = self._catalog.is_passphrase_regenerable(p_name)
            if os.path.exists(save_path) and not regenerable:
                continue

            # Generate secret as it either does not exist yet or is a
            # regenerable secret and does exist but should be rotated.
            passphrase = None
            passphrase_type = self._catalog.get_passphrase_type(p_name)
            prompt = self._catalog.is_passphrase_prompt(p_name)
            profile = self._catalog.get_passphrase_profile(p_name)
            if interactive and prompt:
                auto_allowed = regenerable

                if passphrase_type == 'uuid':  # nosec
                    passphrase = self._prompt_user_passphrase_and_validate(
                        p_name,
                        'UUID',
                        self.validate_uuid,
                        auto_allowed=auto_allowed)

                elif passphrase_type == 'base64':  # nosec
                    passphrase = self._prompt_user_passphrase_and_validate(
                        p_name,
                        'passphrase (b64)',
                        self.validate_base64,
                        auto_allowed=auto_allowed)

                elif passphrase_type == 'passphrase':
                    passphrase = self._prompt_user_passphrase_and_validate(
                        p_name,
                        'passphrase',
                        self.validate_passphrase,
                        auto_allowed=auto_allowed)
            elif not interactive and prompt:
                LOG.debug('Skipping interactive input for %s', p_name)
                continue

            if not passphrase:
                if passphrase_type == 'uuid':  # nosec
                    passphrase = uuidutils.generate_uuid()
                else:
                    passphrase = CryptoString(profile).get_crypto_string(
                        self._catalog.get_length(p_name))
                    if passphrase_type == 'base64':  # nosec
                        # Take the randomly generated string and convert to a
                        # random base64 string
                        passphrase = passphrase.encode()
                        passphrase = base64.b64encode(passphrase).decode()
            docs = list()
            if force_cleartext:
                storage_policy = passphrase_catalog.P_CLEARTEXT
                LOG.warning(
                    "Passphrases for {} will be "
                    "generated in clear text.".format(p_name))
            else:
                storage_policy = self._catalog.get_storage_policy(p_name)

            docs.append(
                self.generate_doc(KIND, p_name, storage_policy, passphrase))
            if storage_policy == passphrase_catalog.P_ENCRYPTED:
                PeglegSecretManagement(
                    docs=docs,
                    generated=True,
                    author=self._author,
                    catalog=self._catalog).encrypt_secrets(save_path)
            else:
                files.write(docs, save_path)

    def _prompt_user_passphrase_and_validate(
            self, p_name, p_type, validation_func, auto_allowed=True):
        passphrase = self.get_interactive_pass(
            p_name, p_type, auto_allowed=auto_allowed)
        validated = self.validate_auto(
            passphrase, auto_allowed) and validation_func(passphrase)
        while not validated:
            passphrase = self.get_interactive_pass(
                p_name, p_type, auto_allowed=auto_allowed)
            validated = self.validate_auto(
                passphrase, auto_allowed) and validation_func(passphrase)
        return passphrase

    @staticmethod
    def get_interactive_pass(p_name, p_type, auto_allowed=True):
        if auto_allowed:
            prompt = ('Input {} for {}. Leave blank to '
                      'auto-generate:\n').format(p_type, p_name)
        else:
            prompt = 'Input {} for {}:\n'.format(p_type, p_name)
        prompt.format(p_name)
        passphrase = getpass(prompt=prompt)
        return passphrase

    @staticmethod
    def validate_base64(passphrase):
        pattern = re.compile(
            "^([A-Za-z0-9+/]{4})*([A-Za-z0-9+/]{4}|[A-Za-z0-9+"
            "/]{3}=|[A-Za-z0-9+/]{2}==)$")
        if not passphrase or len(passphrase) < 1:
            click.echo(
                'Passphrase "{}" is not base64 like.'.format(passphrase))
            return False
        elif pattern.match(passphrase):
            return True
        else:
            click.echo(
                'Passphrase "{}" is not base64 like.'.format(passphrase))
            return False

    @staticmethod
    def validate_uuid(passphrase):
        if uuidutils.is_uuid_like(passphrase):
            return True
        else:
            click.echo('Passphrase "{}" is not UUID like.'.format(passphrase))
            return False

    @staticmethod
    def validate_passphrase(passphrase):
        """Passphrase type is not currently validated"""
        return True

    @staticmethod
    def validate_auto(passphrase, auto_allowed):
        if not passphrase and not auto_allowed:
            click.echo(
                'Documents cannot have autogenerated passphrases when '
                'regenerable is false.')
            return False
        else:
            return True

    @property
    def kind_path(self):
        return KIND_PATH

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

from getpass import getpass
import logging

from pegleg.engine.catalogs import passphrase_catalog
from pegleg.engine.catalogs.passphrase_catalog import PassphraseCatalog
from pegleg.engine.generators.base_generator import BaseGenerator
from pegleg.engine.util import files
from pegleg.engine.util.passphrase import Passphrase
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

    def __init__(self, sitename, save_location, author):
        """Constructor for ``PassphraseGenerator``.

        :param str sitename: Site name for which passphrases are generated.
        :param str save_location: The base directory to store the generated
        passphrase documents.
        :param str author: Identifying name of the author generating new
        certificates.
        """

        super(PassphraseGenerator, self).__init__(
            sitename, save_location, author)
        self._catalog = PassphraseCatalog(
            self._sitename, documents=self._documents)
        self._pass_util = Passphrase()

    def generate(self, interactive=False):
        """
        For each passphrase entry in the passphrase catalog, generate a
        random passphrase string, based on a passphrase specification in the
        catalog. Create a pegleg managed document, wrap the generated
        passphrase document in the pegleg managed document, and encrypt the
        passphrase. Write the wrapped and encrypted document in a file at
        <repo_name>/site/<site_name>/secrets/passphrases/passphrase_name.yaml.
        """
        for p_name in self._catalog.get_passphrase_names:
            passphrase = None
            if interactive:
                passphrase = getpass(
                    prompt="Input passphrase for {}. Leave blank to "
                           "auto-generate:\n".format(p_name))
            if not passphrase:
                passphrase = self._pass_util.get_pass(
                    self._catalog.get_length(p_name))
            docs = list()
            storage_policy = self._catalog.get_storage_policy(p_name)
            docs.append(self.generate_doc(
                KIND,
                p_name,
                storage_policy,
                passphrase))
            save_path = self.get_save_path(p_name)
            if storage_policy == passphrase_catalog.P_ENCRYPTED:
                PeglegSecretManagement(
                    docs=docs, generated=True, author=self._author,
                    catalog=self._catalog).encrypt_secrets(
                    save_path)
            else:
                files.write(save_path, docs)

    @property
    def kind_path(self):
        return KIND_PATH

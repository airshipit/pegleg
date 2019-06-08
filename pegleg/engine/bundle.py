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

import click
from promenade.builder import Builder
from promenade.config import Configuration
from promenade import exceptions

from pegleg.engine.exceptions import GenesisBundleEncryptionException
from pegleg.engine.exceptions import GenesisBundleGenerateException
from pegleg.engine import util
from pegleg.engine.util.pegleg_secret_management import PeglegSecretManagement

LOG = logging.getLogger(__name__)

__all__ = [
    'build_genesis',
]


def build_genesis(build_path, encryption_key, validators, debug, site_name):
    """
    Build the genesis deployment bundle, and store it in ``build_path``.

    Build the genesis.sh script, base65-encode, encrypt and embed the
    site configuration source documents in genesis.sh script.
    If ``validators`` flag should be True, build the bundle validator
    scripts as well.
    Store the built deployment bundle in `build_path`.

    :param str build_path: Directory path of the built genesis deployment
    bundle
    :param str encryption_key: Key to use to encrypt the bundled site
    configuration in genesis.sh script.
    :param bool validators: Whether to generate validator scripts
    :param int debug: pegleg debug level to pass to promenade engine
    for logging.
    :return: None
    """

    # Raise an error if the build path exists. We don't want to overwrite it.
    if os.path.isdir(build_path):
        raise click.ClickException(
            "{} already exists, remove it or specify a new "
            "directory.".format(build_path))
    # Get the list of config files
    LOG.info('=== Building bootstrap scripts ===')

    # Copy the site config, and site secrets to build directory
    os.mkdir(build_path)
    documents = util.definition.documents_for_site(site_name)
    secret_manager = PeglegSecretManagement(docs=documents)
    documents = secret_manager.get_decrypted_secrets()
    try:
        # Use the promenade engine to build and encrypt the genesis bundle
        c = Configuration(
            documents=documents,
            debug=debug,
            substitute=True,
            allow_missing_substitutions=False,
            leave_kubectl=False)
        if c.get_path('EncryptionPolicy:scripts.genesis') and encryption_key:
            Builder(c, validators=validators).build_all(output_dir=build_path)
        else:
            raise GenesisBundleEncryptionException()

    except exceptions.PromenadeException as e:
        LOG.error(
            'Build genesis bundle failed! {}.'.format(e.display(debug=debug)))
        raise GenesisBundleGenerateException()

    LOG.info('=== Done! ===')

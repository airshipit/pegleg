# Copyright 2019 AT&T Intellectual Property.  All other rights reserved.
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

import copy
import os
import shutil
import textwrap
from unittest import mock

import pytest
import yaml

from pegleg import config
from pegleg.engine.catalog import pki_generator
from pegleg.engine.catalog import pki_utility
from pegleg.engine.common import managed_document
from pegleg.engine import secrets
from pegleg.engine.util import files
from tests.unit import test_utils

_SITE_TEST_STRUCTURE = {
    'directories': {
        'secrets': {
            'directories': {
                'passphrases': {
                    'files': {}
                },
            },
        },
        'pki': {
            'files': {}
        }
    },
    'files': {}
}

_SITE_DEFINITION = textwrap.dedent(
    """
    ---
    schema: pegleg/SiteDefinition/v1
    metadata:
      layeringDefinition: {abstract: false, layer: site}
      name: %(sitename)s
      schema: metadata/Document/v1
      storagePolicy: cleartext
    data:
      repositories:
        global:
          revision: v1.0
          url: http://nowhere.com
      site_type: %(sitename)s
    ...
    """)

_LAYERING_DEFINITION = textwrap.dedent(
    """
    ---
    schema: deckhand/LayeringPolicy/v1
    metadata:
      schema: metadata/Control/v1
      name: layering-policy
    data:
      layerOrder:
        - site
    """)

_CA_KEY_NAME = "kubernetes"
_CERT_KEY_NAME = "kubelet-n3"
_KEYPAIR_KEY_NAME = "service-account"

_PKI_CATALOG_CAS = textwrap.dedent(
    """
    ---
    schema: pegleg/PKICatalog/v1
    metadata:
      schema: metadata/Document/v1
      name: cluster-certificates-addition
      layeringDefinition:
        abstract: false
        layer: site
      storagePolicy: cleartext
    data:
      certificate_authorities:
        %s:
          description: CA for Kubernetes components
    ...
    """ % _CA_KEY_NAME)

_PKI_CATALOG_CERTS = textwrap.dedent(
    """
    ---
    schema: pegleg/PKICatalog/v1
    metadata:
      schema: metadata/Document/v1
      name: cluster-certificates-addition
      layeringDefinition:
        abstract: false
        layer: site
      storagePolicy: cleartext
    data:
      certificate_authorities:
        %s:
          description: CA for Kubernetes components
          certificates:
            - document_name: %s
              common_name: system:node:n3
              hosts:
                - n3
                - 192.168.77.13
              groups:
                - system:nodes
    ...
    """ % (_CA_KEY_NAME, _CERT_KEY_NAME))

_PKI_CATALOG_KEYPAIRS = textwrap.dedent(
    """
    ---
    schema: pegleg/PKICatalog/v1
    metadata:
      schema: metadata/Document/v1
      name: cluster-certificates-addition
      layeringDefinition:
        abstract: false
        layer: site
      storagePolicy: cleartext
    data:
      keypairs:
        - name: %s
          description: |
            Service account signing key for use by Kubernetes
            controller-manager.
    ...
    """ % _KEYPAIR_KEY_NAME)

_PKI_CATALOG_EVERYTHING = textwrap.dedent(
    """
    ---
    schema: pegleg/PKICatalog/v1
    metadata:
      schema: metadata/Document/v1
      name: cluster-certificates-addition
      layeringDefinition:
        abstract: false
        layer: site
      storagePolicy: cleartext
    data:
      certificate_authorities:
        %s:
          description: CA for Kubernetes components
          certificates:
            - document_name: %s
              common_name: system:node:n3
              hosts:
                - n3
                - 192.168.77.13
              groups:
                - system:nodes
      keypairs:
        - name: %s
          description: |
            Service account signing key for use by Kubernetes
            controller-manager.
    ...
    """ % (_CA_KEY_NAME, _CERT_KEY_NAME, _KEYPAIR_KEY_NAME))


@pytest.fixture()
def create_tmp_pki_structure(tmpdir):
    """Fixture that creates a temporary site directory structure include pki/
    subfolder for validating PKIGenerator logic.

    :returns: Function pointer, which, when called, creates a temporary file
        structure with pki/ subfolder.

    """
    def _create_tmp_folder_system(sitename, pki_catalog):
        """Creates a temporary site folder system.

        :param str sitename: Name of the site.
        :param str pki_catalog: YAML-formatted string that adheres to
            pki-catalog.yaml structure.
        """
        # Create site directories and files.
        p = tmpdir.mkdir("deployment_files")
        config.set_site_repo(p.strpath)

        site_definition = copy.deepcopy(_SITE_DEFINITION)
        site_definition = site_definition % {'sitename': sitename}

        pki_catalog = copy.deepcopy(pki_catalog)
        pki_catalog = pki_catalog.format(sitename=sitename)

        test_structure = copy.deepcopy(_SITE_TEST_STRUCTURE)
        test_structure['files']['site-definition.yaml'] = yaml.safe_load(
            site_definition)
        test_structure['files']['layering-definition.yaml'] = yaml.safe_load(
            _LAYERING_DEFINITION)
        test_structure['directories']['pki']['files'][
            'pki-catalog.yaml'] = yaml.safe_load(pki_catalog)

        test_path = os.path.join(p.strpath, files._site_path(sitename))
        files._create_tree(test_path, tree=test_structure)

        return p.strpath

    try:
        yield _create_tmp_folder_system
    finally:
        temp_path = config.get_site_repo()
        if temp_path != './' and os.path.exists(temp_path):
            shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture(autouse=True)
def mock_passphrase_and_salt_env_variables(tmpdir):
    rand_passphrase = secrets.generate_crypto_string(length=24)
    rand_salt = secrets.generate_crypto_string(length=24)
    unmocked_env_get = os.environ.get

    def mock_environ_get(key, *args, **kwargs):
        if key == 'PEGLEG_PASSPHRASE':
            return rand_passphrase
        elif key == 'PEGLEG_SALT':
            return rand_salt
        return unmocked_env_get(key, *args, **kwargs)

    mock_env_get = mock.patch(
        'os.environ.get', side_effect=mock_environ_get).start()
    yield
    mock_env_get.stop()


@pytest.mark.skipif(
    not pki_utility.PKIUtility.cfssl_exists(),
    reason='cfssl must be installed to execute these tests')
class TestPKIGenerator(object):
    # TODO(felipemonteiro): Test expiry logic.

    @classmethod
    def setup_class(cls):
        mock.patch.object(
            managed_document,
            '_get_repo_url_and_rev',
            new=lambda: ('fake://github.com/nothing.git', 'master')).start()

    def _validate_documents(self, documents, expected_name, valid_schemas):
        # Always expect 2 of each document (privatekey/publickey).
        assert 2 == len(documents)

        for document in documents:
            # Validate that the wrapped document exists.
            assert 'managedDocument' in document['data']
            assert isinstance(document['data']['managedDocument'], dict)
            wrapped_document = document['data']['managedDocument']

            # Validate the wrapped document data.
            wrapped_schema = wrapped_document['schema']
            wrapped_name = wrapped_document['metadata']['name']

            assert wrapped_schema in valid_schemas
            # Assert that one each of the valid schemas is present.
            valid_schemas.remove(wrapped_schema)
            assert expected_name == wrapped_name

            # Validate the wrapper document data.
            wrapper_schema = document['schema']
            wrapper_name = document['metadata']['name']
            wrapper_storage_policy = document['metadata']['storagePolicy']
            # This document is owned by Pegleg so begins with pegleg.
            assert "pegleg/PeglegManagedDocument/v1" == wrapper_schema
            assert expected_name == wrapper_name
            assert "cleartext" == wrapper_storage_policy

    def _validate_keypairs(self, documents):
        valid_keypair_schemas = [
            # These documents are owned by Deckhand so begin with deckhand.
            "deckhand/PublicKey/v1",
            "deckhand/PrivateKey/v1",
        ]

        def _filter_keypairs(x):
            return (
                x['data']['managedDocument']['schema'] in valid_keypair_schemas
            )

        keypairs = list(filter(_filter_keypairs, documents))
        self._validate_documents(
            keypairs,
            expected_name=_KEYPAIR_KEY_NAME,
            valid_schemas=valid_keypair_schemas)

    def _validate_certificates(self, documents):
        valid_cert_schemas = [
            # These documents are owned by Deckhand so begin with deckhand.
            "deckhand/Certificate/v1",
            "deckhand/CertificateKey/v1",
        ]

        def _filter_certificates(x):
            return (
                x['data']['managedDocument']['schema'] in valid_cert_schemas)

        certificates = list(filter(_filter_certificates, documents))
        self._validate_documents(
            certificates,
            expected_name=_CERT_KEY_NAME,
            valid_schemas=valid_cert_schemas)

    def _validate_certificate_authorities(self, documents):
        valid_ca_schemas = [
            # These documents are owned by Deckhand so begin with deckhand.
            "deckhand/CertificateAuthority/v1",
            "deckhand/CertificateAuthorityKey/v1",
        ]

        def _filter_cas(x):
            return (x['data']['managedDocument']['schema'] in valid_ca_schemas)

        cas = list(filter(_filter_cas, documents))
        self._validate_documents(
            cas, expected_name=_CA_KEY_NAME, valid_schemas=valid_ca_schemas)

    def _aggregate_documents(self, output_paths):
        documents = []
        for output_path in output_paths:
            with open(output_path, 'r') as f:
                documents.extend(list(yaml.safe_load_all(f)))
        return documents

    def _test_pki_generates_cas(self, sitename):
        pkigenerator = pki_generator.PKIGenerator(sitename)
        output_paths = pkigenerator.generate()

        documents = self._aggregate_documents(output_paths)
        assert 2 == len(documents)
        self._validate_certificate_authorities(documents)

        return documents

    def test_pki_generates_cas(self, create_tmp_pki_structure):
        """Validate that PKIGenerator generates CAs."""
        sitename = "test"
        rootpath = create_tmp_pki_structure(sitename, _PKI_CATALOG_CAS)

        self._test_pki_generates_cas(sitename)

    def _test_pki_generates_certificates(self, sitename):
        pkigenerator = pki_generator.PKIGenerator(sitename)
        output_paths = pkigenerator.generate()

        documents = self._aggregate_documents(output_paths)
        assert 4 == len(documents)
        self._validate_certificate_authorities(documents)
        self._validate_certificates(documents)

        return documents

    def test_pki_generates_certificates(self, create_tmp_pki_structure):
        """Validate that PKIGenerator generates certificates (which requires
        generating the CAs as well).
        """
        sitename = "test"
        rootpath = create_tmp_pki_structure(sitename, _PKI_CATALOG_CERTS)

        self._test_pki_generates_certificates(sitename)

    def _test_pki_generates_keypairs(self, sitename):
        pkigenerator = pki_generator.PKIGenerator(sitename)
        output_paths = pkigenerator.generate()

        documents = self._aggregate_documents(output_paths)
        assert 2 == len(documents)
        self._validate_keypairs(documents)

        return documents

    def test_pki_generates_keypairs(self, create_tmp_pki_structure):
        """Validate that PKIGenerator generates keypairs."""
        sitename = "test"
        rootpath = create_tmp_pki_structure(sitename, _PKI_CATALOG_KEYPAIRS)

        self._test_pki_generates_keypairs(sitename)

    def _test_pki_generates_everything(self, sitename):
        pkigenerator = pki_generator.PKIGenerator(sitename)
        output_paths = pkigenerator.generate()

        documents = self._aggregate_documents(output_paths)
        assert 6 == len(documents)
        self._validate_keypairs(documents)
        self._validate_certificate_authorities(documents)
        self._validate_certificates(documents)

        return documents

    def test_pki_generates_everything(self, create_tmp_pki_structure):
        """Validate that PKIGenerator generates certs, CAs, and keypairs
        (everything) all at once.
        """
        sitename = "test"
        rootpath = create_tmp_pki_structure(sitename, _PKI_CATALOG_EVERYTHING)

        self._test_pki_generates_everything(sitename)

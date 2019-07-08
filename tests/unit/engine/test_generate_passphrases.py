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
import os
import tempfile
from unittest import mock
import uuid

from cryptography import fernet
import pytest
from testfixtures import log_capture
import yaml

from pegleg.engine.generators.passphrase_generator import PassphraseGenerator
from pegleg.engine.util.cryptostring import CryptoString
from pegleg.engine.util import encryption
from pegleg.engine import util
import pegleg

TEST_PASSPHRASES_CATALOG = yaml.safe_load(
    """
---
schema: pegleg/PassphraseCatalog/v1
metadata:
  schema: metadata/Document/v1
  name: cluster-passphrases
  layeringDefinition:
    abstract: false
    layer: site
  storagePolicy: cleartext
data:
  passphrases:
    - description: 'short description of the passphrase'
      document_name: ceph_swift_keystone_password
      encrypted: true
    - description: 'short description of the passphrase'
      document_name: ucp_keystone_admin_password
      encrypted: true
      length: 24
    - description: 'short description of the passphrase'
      document_name: osh_barbican_oslo_db_password
      encrypted: true
      length: 23
    - description: 'short description of the passphrase'
      document_name: osh_cinder_password
      encrypted: true
      length: 25
    - description: 'short description of the passphrase'
      document_name: osh_oslo_db_admin_password
      encrypted: true
      length: 0
    - description: 'short description of the passphrase'
      document_name: osh_placement_password
      encrypted: true
      length: 32
...
""")

TEST_GLOBAL_PASSPHRASES_CATALOG = yaml.safe_load(
    """
---
schema: pegleg/PassphraseCatalog/v1
metadata:
  schema: metadata/Document/v1
  name: cluster-passphrases
  layeringDefinition:
    abstract: false
    layer: global
  storagePolicy: cleartext
data:
  passphrases:
    - description: 'description of passphrase from global'
      document_name: passphrase_from_global
      encrypted: true
...
""")

TEST_TYPES_CATALOG = yaml.safe_load(
    """
---
schema: pegleg/PassphraseCatalog/v1
metadata:
  schema: metadata/Document/v1
  name: cluster-passphrases
  layeringDefinition:
    abstract: false
    layer: global
  storagePolicy: cleartext
data:
  passphrases:
    - description: 'description of base64 required passphrases'
      document_name: base64_encoded_passphrase_doc
      encrypted: true
      type: base64
    - description: 'description of uuid secret'
      document_name: uuid_passphrase_doc
      encrypted: true
      encoding: none
      type: uuid
    - description: 'description of random passphrase'
      document_name: passphrase_doc
      encrypted: true
      type: passphrase
    - description: 'description of default random passphrase'
      document_name: default_passphrase_doc
      encrypted: true
...
""")

TEST_REPOSITORIES = {
    'repositories': {
        'global': {
            'revision': '843d1a50106e1f17f3f722e2ef1634ae442fe68f',
            'url': 'ssh://REPO_USERNAME@gerrit:29418/aic-clcp-manifests.git'
        },
        'secrets': {
            'revision': 'master',
            'url': (
                'ssh://REPO_USERNAME@gerrit:29418/aic-clcp-security-'
                'manifests.git')
        }
    }
}

TEST_SITE_DEFINITION = {
    'data': {
        'revision': 'v1.0',
        'site_type': 'cicd',
    },
    'metadata': {
        'layeringDefinition': {
            'abstract': 'false',
            'layer': 'site',
        },
        'name': 'test-site',
        'schema': 'metadata/Document/v1',
        'storagePolicy': 'cleartext',
    },
    'schema': 'pegleg/SiteDefinition/v1',
}

TEST_SITE_DOCUMENTS = [TEST_SITE_DEFINITION, TEST_PASSPHRASES_CATALOG]
TEST_GLOBAL_SITE_DOCUMENTS = [
    TEST_SITE_DEFINITION, TEST_GLOBAL_PASSPHRASES_CATALOG
]
TEST_TYPE_SITE_DOCUMENTS = [TEST_SITE_DEFINITION, TEST_TYPES_CATALOG]


@mock.patch.object(
    util.definition,
    'documents_for_site',
    autospec=True,
    return_value=TEST_SITE_DOCUMENTS)
@mock.patch.object(
    pegleg.config,
    'get_site_repo',
    autospec=True,
    return_value='cicd_site_repo')
@mock.patch.object(
    util.definition,
    'site_files',
    autospec=True,
    return_value=[
        'cicd_site_repo/site/cicd/passphrases/passphrase-catalog.yaml',
    ])
@mock.patch.dict(
    os.environ, {
        'PEGLEG_PASSPHRASE': 'ytrr89erARAiPE34692iwUMvWqqBvC',
        'PEGLEG_SALT': 'MySecretSalt1234567890]['
    })
def test_generate_passphrases(*_):
    _dir = tempfile.mkdtemp()
    os.makedirs(os.path.join(_dir, 'cicd_site_repo'), exist_ok=True)
    PassphraseGenerator('cicd', _dir, 'test_author').generate()

    for passphrase in TEST_PASSPHRASES_CATALOG['data']['passphrases']:
        passphrase_file_name = '{}.yaml'.format(passphrase['document_name'])
        passphrase_file_path = os.path.join(
            _dir, 'site', 'cicd', 'secrets', 'passphrases',
            passphrase_file_name)
        assert os.path.isfile(passphrase_file_path)
        with open(passphrase_file_path) as stream:
            doc = yaml.safe_load(stream)
            assert doc['schema'] == 'pegleg/PeglegManagedDocument/v1'
            assert doc['metadata']['storagePolicy'] == 'cleartext'
            assert 'encrypted' in doc['data']
            assert doc['data']['encrypted']['by'] == 'test_author'
            assert 'generated' in doc['data']
            assert doc['data']['generated']['by'] == 'test_author'
            assert 'managedDocument' in doc['data']
            assert doc['data']['managedDocument']['metadata'][
                'storagePolicy'] == 'encrypted'
            decrypted_passphrase = encryption.decrypt(
                doc['data']['managedDocument']['data'],
                os.environ['PEGLEG_PASSPHRASE'].encode(),
                os.environ['PEGLEG_SALT'].encode())
            if passphrase_file_name == 'osh_placement_password.yaml':
                assert len(decrypted_passphrase) == 32
            elif passphrase_file_name == 'osh_cinder_password.yaml':
                assert len(decrypted_passphrase) == 25
            else:
                assert len(decrypted_passphrase) == 24


@log_capture()
def test_generate_passphrases_exception(capture):
    unenc_data = uuid.uuid4().bytes
    passphrase1 = uuid.uuid4().bytes
    passphrase2 = uuid.uuid4().bytes
    salt1 = uuid.uuid4().bytes
    salt2 = uuid.uuid4().bytes

    # Generate random data and encrypt it
    enc_data = encryption.encrypt(unenc_data, passphrase1, salt1)

    # Decrypt using the wrong key to see to see the InvalidToken error
    with pytest.raises(fernet.InvalidToken):
        encryption.decrypt(enc_data, passphrase2, salt2)
    capture.check(
        (
            'pegleg.engine.util.encryption', 'ERROR', (
                'Signature verification to decrypt secrets failed. '
                'Please check your provided passphrase and salt and '
                'try again.')))


@mock.patch.object(
    util.definition,
    'documents_for_site',
    autospec=True,
    return_value=TEST_GLOBAL_SITE_DOCUMENTS)
@mock.patch.object(
    pegleg.config,
    'get_site_repo',
    autospec=True,
    return_value='cicd_site_repo')
@mock.patch.object(
    util.definition,
    'site_files',
    autospec=True,
    return_value=[
        'cicd_global_repo/site/cicd/passphrases/passphrase-catalog.yaml',
    ])
@mock.patch.dict(
    os.environ, {
        'PEGLEG_PASSPHRASE': 'ytrr89erARAiPE34692iwUMvWqqBvC',
        'PEGLEG_SALT': 'MySecretSalt1234567890]['
    })
def test_global_passphrase_catalog(*_):
    _dir = tempfile.mkdtemp()
    os.makedirs(os.path.join(_dir, 'cicd_site_repo'), exist_ok=True)
    PassphraseGenerator('cicd', _dir, 'test_author').generate()

    for passphrase in TEST_GLOBAL_PASSPHRASES_CATALOG['data']['passphrases']:
        passphrase_file_name = '{}.yaml'.format(passphrase['document_name'])
        passphrase_file_path = os.path.join(
            _dir, 'site', 'cicd', 'secrets', 'passphrases',
            passphrase_file_name)
        assert os.path.isfile(passphrase_file_path)
        with open(passphrase_file_path) as stream:
            doc = yaml.safe_load(stream)
            assert doc['schema'] == 'pegleg/PeglegManagedDocument/v1'
            assert doc['metadata']['storagePolicy'] == 'cleartext'
            assert 'encrypted' in doc['data']
            assert doc['data']['encrypted']['by'] == 'test_author'
            assert 'generated' in doc['data']
            assert doc['data']['generated']['by'] == 'test_author'
            assert 'managedDocument' in doc['data']
            assert doc['data']['managedDocument']['metadata'][
                'storagePolicy'] == 'encrypted'
            decrypted_passphrase = encryption.decrypt(
                doc['data']['managedDocument']['data'],
                os.environ['PEGLEG_PASSPHRASE'].encode(),
                os.environ['PEGLEG_SALT'].encode())
            if passphrase_file_name == "passphrase_from_global.yaml":
                assert len(decrypted_passphrase) == 24


@mock.patch.object(
    util.definition,
    'documents_for_site',
    autospec=True,
    return_value=TEST_TYPE_SITE_DOCUMENTS)
@mock.patch.object(
    pegleg.config,
    'get_site_repo',
    autospec=True,
    return_value='cicd_site_repo')
@mock.patch.object(
    util.definition,
    'site_files',
    autospec=True,
    return_value=[
        'cicd_global_repo/site/cicd/passphrases/passphrase-catalog.yaml',
    ])
@mock.patch.dict(
    os.environ, {
        'PEGLEG_PASSPHRASE': 'ytrr89erARAiPE34692iwUMvWqqBvC',
        'PEGLEG_SALT': 'MySecretSalt1234567890]['
    })
def test_uuid_passphrase_catalog(*_):
    _dir = tempfile.mkdtemp()
    os.makedirs(os.path.join(_dir, 'cicd_site_repo'), exist_ok=True)
    PassphraseGenerator('cicd', _dir, 'test_author').generate()

    for passphrase in TEST_TYPES_CATALOG['data']['passphrases']:
        passphrase_file_name = '{}.yaml'.format(passphrase['document_name'])
        passphrase_file_path = os.path.join(
            _dir, 'site', 'cicd', 'secrets', 'passphrases',
            passphrase_file_name)
        assert os.path.isfile(passphrase_file_path)
        with open(passphrase_file_path) as stream:
            doc = yaml.safe_load(stream)
            decrypted_passphrase = encryption.decrypt(
                doc['data']['managedDocument']['data'],
                os.environ['PEGLEG_PASSPHRASE'].encode(),
                os.environ['PEGLEG_SALT'].encode())
            if passphrase_file_name == "uuid_passphrase_doc.yaml":
                assert uuid.UUID(decrypted_passphrase.decode()).version == 4

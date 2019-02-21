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

import os
import tempfile

import mock
import string
import yaml

from pegleg.engine.util.cryptostring import CryptoString
from pegleg.engine.generators.passphrase_generator import PassphraseGenerator
from pegleg.engine.util import encryption
from pegleg.engine import util
import pegleg
from pegleg.engine.util.pegleg_secret_management import ENV_PASSPHRASE
from pegleg.engine.util.pegleg_secret_management import ENV_SALT

TEST_PASSPHRASES_CATALOG = yaml.load("""
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

TEST_REPOSITORIES = {
    'repositories': {
        'global': {
            'revision': '843d1a50106e1f17f3f722e2ef1634ae442fe68f',
            'url': 'ssh://REPO_USERNAME@gerrit:29418/aic-clcp-manifests.git'
        },
        'secrets': {
            'revision': 'master',
            'url': ('ssh://REPO_USERNAME@gerrit:29418/aic-clcp-security-'
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


def test_cryptostring_default_len():
    s_util = CryptoString()
    s = s_util.get_crypto_string()
    assert len(s) == 24
    alphabet = set(string.punctuation + string.ascii_letters + string.digits)
    assert any(c in alphabet for c in s)


def test_cryptostring_short_len():
    s_util = CryptoString()
    s = s_util.get_crypto_string(0)
    assert len(s) == 24
    s = s_util.get_crypto_string(23)
    assert len(s) == 24
    s = s_util.get_crypto_string(-1)
    assert len(s) == 24


def test_cryptostring_long_len():
    s_util = CryptoString()
    s = s_util.get_crypto_string(25)
    assert len(s) == 25
    s = s_util.get_crypto_string(128)
    assert len(s) == 128


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
        'cicd_site_repo/site/cicd/passphrases/passphrase-catalog.yaml', ])
@mock.patch.dict(os.environ, {
    ENV_PASSPHRASE: 'ytrr89erARAiPE34692iwUMvWqqBvC',
    ENV_SALT: 'MySecretSalt'})
def test_generate_passphrases(*_):
    dir = tempfile.mkdtemp()
    os.makedirs(os.path.join(dir, 'cicd_site_repo'), exist_ok=True)
    PassphraseGenerator('cicd', dir, 'test_author').generate()

    for passphrase in TEST_PASSPHRASES_CATALOG['data']['passphrases']:
        passphrase_file_name = '{}.yaml'.format(passphrase['document_name'])
        passphrase_file_path = os.path.join(dir, 'site', 'cicd', 'secrets',
                                            'passphrases',
                                            passphrase_file_name)
        assert os.path.isfile(passphrase_file_path)
        with open(passphrase_file_path) as stream:
            doc = yaml.load(stream)
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

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

import click
import os
import tempfile

import mock
import pytest
import yaml

from pegleg.engine.util import encryption as crypt
from tests.unit import test_utils
from pegleg.engine.util.pegleg_managed_document import \
    PeglegManagedSecretsDocument
from pegleg.engine.util.pegleg_secret_management import PeglegSecretManagement
from pegleg.engine.util.pegleg_secret_management import ENV_PASSPHRASE
from pegleg.engine.util.pegleg_secret_management import ENV_SALT
from tests.unit.fixtures import temp_path
from pegleg.engine.util import files

TEST_DATA = """
---
schema: deckhand/Passphrase/v1
metadata:
  schema: metadata/Document/v1
  name: osh_addons_keystone_ranger-agent_password
  layeringDefinition:
    abstract: false
    layer: site
  storagePolicy: encrypted
data: 512363f37eab654313991174aef9f867d
...
"""


def test_encrypt_and_decrypt():
    data = test_utils.rand_name("this is an example of un-encrypted "
                                "data.", "pegleg").encode()
    passphrase = test_utils.rand_name("passphrase1", "pegleg").encode()
    salt = test_utils.rand_name("salt1", "pegleg").encode()
    enc1 = crypt.encrypt(data, passphrase, salt)
    dec1 = crypt.decrypt(enc1, passphrase, salt)
    assert data == dec1
    enc2 = crypt.encrypt(dec1, passphrase, salt)
    dec2 = crypt.decrypt(enc2, passphrase, salt)
    assert data == dec2


@mock.patch.dict(os.environ, {
    ENV_PASSPHRASE: 'aShortPassphrase',
    ENV_SALT: 'MySecretSalt'
})
def test_short_passphrase():
    with pytest.raises(
            click.ClickException,
            match=r'.*is not at least 24-character long.*'):
        PeglegSecretManagement('file_path')


def test_pegleg_secret_management_constructor():
    test_data = yaml.load(TEST_DATA)
    doc = PeglegManagedSecretsDocument(test_data)
    assert doc.is_storage_policy_encrypted()
    assert not doc.is_encrypted()


def test_pegleg_secret_management_constructor_with_invalid_arguments():
    with pytest.raises(ValueError) as err_info:
        PeglegSecretManagement(file_path=None, docs=None)
    assert 'Either `file_path` or `docs` must be specified.' in str(
        err_info.value)
    with pytest.raises(ValueError) as err_info:
        PeglegSecretManagement(file_path='file_path', docs=['doc1'])
    assert 'Either `file_path` or `docs` must be specified.' in str(
        err_info.value)


@mock.patch.dict(os.environ, {
    ENV_PASSPHRASE: 'ytrr89erARAiPE34692iwUMvWqqBvC',
    ENV_SALT: 'MySecretSalt'
})
def test_encrypt_decrypt_using_file_path(temp_path):
    # write the test data to temp file
    test_data = list(yaml.safe_load_all(TEST_DATA))
    file_path = os.path.join(temp_path, 'secrets_file.yaml')
    files.write(file_path, test_data)
    save_path = os.path.join(temp_path, 'encrypted_secrets_file.yaml')

    # encrypt documents and validate that they were encrypted
    doc_mgr = PeglegSecretManagement(file_path=file_path)
    doc_mgr.encrypt_secrets(save_path, 'test_author')
    doc = doc_mgr.documents[0]
    assert doc.is_encrypted()
    assert doc.data['encrypted']['by'] == 'test_author'

    # decrypt documents and validate that they were decrypted
    doc_mgr = PeglegSecretManagement(save_path)
    decrypted_data = doc_mgr.get_decrypted_secrets()
    assert test_data[0]['data'] == decrypted_data[0]['data']
    assert test_data[0]['schema'] == decrypted_data[0]['schema']


@mock.patch.dict(os.environ, {
    ENV_PASSPHRASE: 'ytrr89erARAiPE34692iwUMvWqqBvC',
    ENV_SALT: 'MySecretSalt'
})
def test_encrypt_decrypt_using_docs(temp_path):
    # write the test data to temp file
    test_data = list(yaml.safe_load_all(TEST_DATA))
    save_path = os.path.join(temp_path, 'encrypted_secrets_file.yaml')

    # encrypt documents and validate that they were encrypted
    doc_mgr = PeglegSecretManagement(docs=test_data)
    doc_mgr.encrypt_secrets(save_path, 'test_author')
    doc = doc_mgr.documents[0]
    assert doc.is_encrypted()
    assert doc.data['encrypted']['by'] == 'test_author'

    # read back the encrypted file
    with open(save_path) as stream:
        encrypted_data = list(yaml.safe_load_all(stream))

    # decrypt documents and validate that they were decrypted
    doc_mgr = PeglegSecretManagement(docs=encrypted_data)
    decrypted_data = doc_mgr.get_decrypted_secrets()
    assert test_data[0]['data'] == decrypted_data[0]['data']
    assert test_data[0]['schema'] == decrypted_data[0]['schema']
    assert test_data[0]['metadata']['name'] == decrypted_data[0]['metadata'][
        'name']
    assert test_data[0]['metadata']['storagePolicy'] == decrypted_data[0][
        'metadata']['storagePolicy']

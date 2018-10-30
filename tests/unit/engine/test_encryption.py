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
from pegleg.engine import secrets
from pegleg.engine.util.pegleg_managed_document import \
    PeglegManagedSecretsDocument
from pegleg.engine.util.pegleg_secret_management import PeglegSecretManagement
from pegleg.engine.util.pegleg_secret_management import ENV_PASSPHRASE
from pegleg.engine.util.pegleg_secret_management import ENV_SALT

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


@mock.patch.dict(os.environ, {ENV_PASSPHRASE:'aShortPassphrase',
                              ENV_SALT: 'MySecretSalt'})
def test_short_passphrase():
    with pytest.raises(click.ClickException,
                       match=r'.*is not at least 24-character long.*'):
        PeglegSecretManagement('file_path')


def test_PeglegManagedDocument():
    test_data = yaml.load(TEST_DATA)
    doc = PeglegManagedSecretsDocument(test_data)
    assert doc.is_storage_policy_encrypted() is True
    assert doc.is_encrypted() is False


@mock.patch.dict(os.environ, {ENV_PASSPHRASE:'ytrr89erARAiPE34692iwUMvWqqBvC',
                              ENV_SALT: 'MySecretSalt'})
def test_encrypt_document():
    # write the test data to temp file
    test_data = yaml.load(TEST_DATA)
    dir = tempfile.mkdtemp()
    file_path = os.path.join(dir, 'secrets_file.yaml')
    save_path = os.path.join(dir, 'encrypted_secrets_file.yaml')
    with open(file_path, 'w') as stream:
        yaml.dump(test_data,
                  stream,
                  explicit_start=True,
                  explicit_end=True,
                  default_flow_style=False)
    # read back the secrets data file and encrypt it
    doc_mgr = PeglegSecretManagement(file_path)
    doc_mgr.encrypt_secrets(save_path, 'test_author')
    doc = doc_mgr.documents[0]
    assert doc.is_encrypted()
    assert doc.data['encrypted']['by'] == 'test_author'

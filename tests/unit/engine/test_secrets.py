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
from os import listdir
from unittest import mock

import pytest
import yaml

from pegleg import config
from pegleg.engine.catalog.pki_generator import PKIGenerator
from pegleg.engine.catalog import pki_utility
from pegleg.engine import exceptions
from pegleg.engine import secrets
from pegleg.engine.util import encryption as crypt, git
from pegleg.engine.util import files
from pegleg.engine.util.pegleg_managed_document import \
    PeglegManagedSecretsDocument
from pegleg.engine.util.pegleg_secret_management import PeglegSecretManagement
from tests.unit import test_utils
from tests.unit.test_cli import TEST_PARAMS

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

TEST_GLOBAL_DATA = """
---
schema: deckhand/Passphrase/v1
metadata:
  schema: metadata/Document/v1
  name: osh_addons_keystone_ranger-agent_password
  layeringDefinition:
    abstract: false
    layer: global
  storagePolicy: encrypted
data: 512363f37eab654313991174aef9f867d
...
"""

GLOBAL_PASSPHRASE_SALT_DOC = """
---
schema: deckhand/Passphrase/v1
metadata:
  schema: metadata/Document/v1
  name: global_passphrase
  layeringDefinition:
    abstract: false
    layer: site
  storagePolicy: encrypted
data: TbKYNtM@3gXpL=AFLAwU?&Ey
...
---
schema: deckhand/Passphrase/v1
metadata:
  schema: metadata/Document/v1
  name: global_salt
  layeringDefinition:
    abstract: false
    layer: site
  storagePolicy: encrypted
data: h3=DQ#GNYEuCvybgpfW7ZxAP
...
"""

GLOBAL_SALT_DOC = """
---
schema: deckhand/Passphrase/v1
metadata:
  schema: metadata/Document/v1
  name: global_salt
  layeringDefinition:
    abstract: false
    layer: site
  storagePolicy: encrypted
data: h3=DQ#GNYEuCvybgpfW7ZxAP
...
"""


def test_encrypt_and_decrypt():
    data = test_utils.rand_name(
        "this is an example of un-encrypted "
        "data.", "pegleg").encode()
    passphrase = test_utils.rand_name("passphrase1", "pegleg").encode()
    salt = test_utils.rand_name("salt1", "pegleg").encode()
    enc1 = crypt.encrypt(data, passphrase, salt)
    dec1 = crypt.decrypt(enc1, passphrase, salt)
    assert data == dec1
    enc2 = crypt.encrypt(dec1, passphrase, salt)
    dec2 = crypt.decrypt(enc2, passphrase, salt)
    assert data == dec2
    passphrase2 = test_utils.rand_name("passphrase2", "pegleg").encode()
    salt2 = test_utils.rand_name("salt2", "pegleg").encode()
    enc3 = crypt.encrypt(dec2, passphrase2, salt2)
    dec3 = crypt.decrypt(enc3, passphrase2, salt2)
    assert data == dec3
    assert data != enc3


@mock.patch.dict(
    os.environ, {
        'PEGLEG_PASSPHRASE': 'aShortPassphrase',
        'PEGLEG_SALT': 'MySecretSalt1234567890]['
    })
def test_short_passphrase():
    with pytest.raises(exceptions.PassphraseInsufficientLengthException):
        PeglegSecretManagement(file_path='file_path', author='test_author')


@mock.patch.dict(
    os.environ, {
        'PEGLEG_PASSPHRASE': 'ytrr89erARAiPE34692iwUMvWqqBvC',
        'PEGLEG_SALT': 'aShortSalt'
    })
def test_short_salt():
    with pytest.raises(exceptions.SaltInsufficientLengthException):
        PeglegSecretManagement(file_path='file_path', author='test_author')


@mock.patch.dict(
    os.environ, {
        'PEGLEG_PASSPHRASE': 'ytrr89erARAiPE34692iwUMvWqqBvC',
        'PEGLEG_SALT': 'MySecretSalt1234567890]['
    })
def test_secret_encrypt_and_decrypt(temp_deployment_files, tmpdir):
    site_dir = tmpdir.join("deployment_files", "site", "cicd")
    passphrase_doc = """---
schema: deckhand/Passphrase/v1
metadata:
  schema: metadata/Document/v1
  name: {0}
  storagePolicy: {1}
  layeringDefinition:
    abstract: False
    layer: {2}
data: {0}-password
...
""".format("cicd-passphrase-encrypted", "encrypted", "site")
    with open(os.path.join(str(site_dir), 'secrets',
                           'passphrases',
                           'cicd-passphrase-encrypted.yaml'), "w") \
            as outfile:
        outfile.write(passphrase_doc)

    save_location = tmpdir.mkdir("encrypted_files")
    save_location_str = str(save_location)

    secrets.encrypt(save_location_str, "pytest", "cicd")
    encrypted_files = listdir(save_location_str)
    assert len(encrypted_files) > 0

    encrypted_path = str(
        save_location.join(
            "site/cicd/secrets/passphrases/"
            "cicd-passphrase-encrypted.yaml"))
    decrypted = secrets.decrypt(encrypted_path)
    assert yaml.safe_load(decrypted[encrypted_path])['data'] == yaml.safe_load(
        passphrase_doc)['data']


@mock.patch.dict(
    os.environ, {
        'PEGLEG_PASSPHRASE': 'ytrr89erARAiPE34692iwUMvWqqBvC',
        'PEGLEG_SALT': 'MySecretSalt1234567890]['
    })
def test_pegleg_secret_management_constructor():
    test_data = yaml.safe_load(TEST_DATA)
    doc = PeglegManagedSecretsDocument(test_data)
    assert doc.is_storage_policy_encrypted()
    assert not doc.is_encrypted()


@mock.patch.dict(
    os.environ, {
        'PEGLEG_PASSPHRASE': 'ytrr89erARAiPE34692iwUMvWqqBvC',
        'PEGLEG_SALT': 'MySecretSalt1234567890]['
    })
def test_pegleg_secret_management_constructor_with_invalid_arguments():
    with pytest.raises(ValueError) as err_info:
        PeglegSecretManagement(file_path=None, docs=None)
    assert 'Either `file_path` or `docs` must be specified.' in str(
        err_info.value)
    with pytest.raises(ValueError) as err_info:
        PeglegSecretManagement(file_path='file_path', docs=['doc1'])
    assert 'Either `file_path` or `docs` must be specified.' in str(
        err_info.value)
    with pytest.raises(ValueError) as err_info:
        PeglegSecretManagement(
            file_path='file_path', generated=True, author='test_author')
    assert 'If the document is generated, author and catalog must be ' \
           'specified.' in str(err_info.value)
    with pytest.raises(ValueError) as err_info:
        PeglegSecretManagement(docs=['doc'], generated=True)
    assert 'If the document is generated, author and catalog must be ' \
           'specified.' in str(err_info.value)
    with pytest.raises(ValueError) as err_info:
        PeglegSecretManagement(
            docs=['doc'], generated=True, author='test_author')
    assert 'If the document is generated, author and catalog must be ' \
           'specified.' in str(err_info.value)
    with pytest.raises(ValueError) as err_info:
        PeglegSecretManagement(docs=['doc'], generated=True, catalog='catalog')
    assert 'If the document is generated, author and catalog must be ' \
           'specified.' in str(err_info.value)


@mock.patch.dict(
    os.environ, {
        'PEGLEG_PASSPHRASE': 'ytrr89erARAiPE34692iwUMvWqqBvC',
        'PEGLEG_SALT': 'MySecretSalt1234567890]['
    })
def test_pegleg_secret_management_double_encrypt():
    encrypted_doc = PeglegSecretManagement(
        docs=[yaml.safe_load(TEST_DATA)]).get_encrypted_secrets()[0][0]
    encrypted_doc_2 = PeglegSecretManagement(
        docs=[encrypted_doc]).get_encrypted_secrets()[0][0]
    assert encrypted_doc == encrypted_doc_2


@mock.patch.dict(
    os.environ, {
        'PEGLEG_PASSPHRASE': 'ytrr89erARAiPE34692iwUMvWqqBvC',
        'PEGLEG_SALT': 'MySecretSalt1234567890]['
    })
def test_encrypt_decrypt_using_file_path(tmpdir):
    # write the test data to temp file
    test_data = list(yaml.safe_load_all(TEST_DATA))
    file_path = os.path.join(tmpdir, 'secrets_file.yaml')
    files.write(test_data, file_path)
    save_path = os.path.join(tmpdir, 'encrypted_secrets_file.yaml')

    # encrypt documents and validate that they were encrypted
    doc_mgr = PeglegSecretManagement(file_path=file_path, author='test_author')
    doc_mgr.encrypt_secrets(save_path)
    doc = doc_mgr.documents[0]
    assert doc.is_encrypted()
    assert doc.data['encrypted']['by'] == 'test_author'

    # decrypt documents and validate that they were decrypted
    doc_mgr = PeglegSecretManagement(file_path=file_path, author='test_author')
    doc_mgr.encrypt_secrets(save_path)
    # read back the encrypted file
    doc_mgr = PeglegSecretManagement(file_path=save_path, author='test_author')
    decrypted_data = doc_mgr.get_decrypted_secrets()
    assert test_data[0]['data'] == decrypted_data[0]['data']
    assert test_data[0]['schema'] == decrypted_data[0]['schema']


@mock.patch.dict(
    os.environ, {
        'PEGLEG_PASSPHRASE': 'ytrr89erARAiPE34692iwUMvWqqBvC',
        'PEGLEG_SALT': 'MySecretSalt1234567890]['
    })
def test_encrypt_decrypt_using_docs(tmpdir):
    # write the test data to temp file
    test_data = list(yaml.safe_load_all(TEST_DATA))
    save_path = os.path.join(tmpdir, 'encrypted_secrets_file.yaml')

    # encrypt documents and validate that they were encrypted
    doc_mgr = PeglegSecretManagement(docs=test_data, author='test_author')
    doc_mgr.encrypt_secrets(save_path)
    doc = doc_mgr.documents[0]
    assert doc.is_encrypted()
    assert doc.data['encrypted']['by'] == 'test_author'

    # read back the encrypted file
    with open(save_path) as stream:
        encrypted_data = list(yaml.safe_load_all(stream))

    # decrypt documents and validate that they were decrypted
    doc_mgr = PeglegSecretManagement(docs=encrypted_data, author='test_author')
    decrypted_data = doc_mgr.get_decrypted_secrets()
    assert test_data[0]['data'] == decrypted_data[0]['data']
    assert test_data[0]['schema'] == decrypted_data[0]['schema']
    assert test_data[0]['metadata']['name'] == decrypted_data[0]['metadata'][
        'name']


@pytest.mark.skipif(
    not pki_utility.PKIUtility.cfssl_exists(),
    reason='cfssl must be installed to execute these tests')
@mock.patch.dict(
    os.environ, {
        'PEGLEG_PASSPHRASE': 'ytrr89erARAiPE34692iwUMvWqqBvC',
        'PEGLEG_SALT': 'MySecretSalt1234567890]['
    })
def test_generate_pki_using_local_repo_path(temp_deployment_files):
    """Validates ``generate-pki`` action using local repo path."""
    # Scenario:
    #
    # 1) Generate PKI using local repo path

    repo_path = str(
        git.git_handler(TEST_PARAMS["repo_url"], ref=TEST_PARAMS["repo_rev"]))
    with mock.patch.dict(config.GLOBAL_CONTEXT, {"site_repo": repo_path}):
        pki_generator = PKIGenerator(
            duration=365, sitename=TEST_PARAMS["site_name"])
        generated_files = pki_generator.generate()

        assert len(generated_files), 'No secrets were generated'
        for generated_file in generated_files:
            with open(generated_file, 'r') as f:
                result = yaml.safe_load_all(f)  # Validate valid YAML.
                assert list(result), "%s file is empty" % generated_file.name


@pytest.mark.skipif(
    not pki_utility.PKIUtility.cfssl_exists(),
    reason='cfssl must be installed to execute these tests')
@mock.patch.dict(
    os.environ, {
        'PEGLEG_PASSPHRASE': 'ytrr89erARAiPE34692iwUMvWqqBvC',
        'PEGLEG_SALT': 'MySecretSalt1234567890]['
    })
def test_check_expiry(temp_deployment_files):
    """ Validates check_expiry """
    repo_path = str(
        git.git_handler(TEST_PARAMS["repo_url"], ref=TEST_PARAMS["repo_rev"]))
    with mock.patch.dict(config.GLOBAL_CONTEXT, {"site_repo": repo_path}):
        pki_generator = PKIGenerator(
            duration=365, sitename=TEST_PARAMS["site_name"])
        generated_files = pki_generator.generate()

        pki_util = pki_utility.PKIUtility(duration=0)

        assert len(generated_files), 'No secrets were generated'
        for generated_file in generated_files:
            if "certificate" not in generated_file:
                continue
            with open(generated_file, 'r') as f:
                results = yaml.safe_load_all(f)  # Validate valid YAML.
                results = PeglegSecretManagement(
                    docs=results).get_decrypted_secrets()
                for result in results:
                    if result['schema'] == \
                            "deckhand/Certificate/v1":
                        cert = result['data']
                        cert_info = pki_util.check_expiry(cert)
                        assert cert_info['expired'] is False, \
                            "%s is expired/expiring on %s" % \
                            (result['metadata']['name'],
                             cert_info['expiry_date'])


@mock.patch.dict(
    os.environ, {
        'PEGLEG_PASSPHRASE': 'ytrr89erARAiPE34692iwUMvWqqBvC',
        'PEGLEG_SALT': 'MySecretSalt1234567890]['
    })
def test_get_global_creds_missing_creds(temp_deployment_files, tmpdir):
    # Create site files
    site_dir = tmpdir.join("deployment_files", "site", "cicd")

    save_location = tmpdir.mkdir("encrypted_site_files")
    save_location_str = str(save_location)

    # Capture global credentials, verify they are not present and we default
    # to site credentials instead.
    passphrase, salt = secrets.get_global_creds("cicd")
    assert passphrase.decode() == 'ytrr89erARAiPE34692iwUMvWqqBvC'
    assert salt.decode() == 'MySecretSalt1234567890]['


@mock.patch.dict(
    os.environ, {
        'PEGLEG_PASSPHRASE': 'ytrr89erARAiPE34692iwUMvWqqBvC',
        'PEGLEG_SALT': 'MySecretSalt1234567890]['
    })
def test_get_global_creds_missing_pass(temp_deployment_files, tmpdir):
    # Create site files
    site_dir = tmpdir.join("deployment_files", "site", "cicd")

    # Create global salt file
    with open(os.path.join(str(site_dir), 'secrets', 'passphrases',
                           'cicd-global-passphrase-encrypted.yaml'),
              "w") as outfile:
        outfile.write(GLOBAL_SALT_DOC)

    save_location = tmpdir.mkdir("encrypted_site_files")
    save_location_str = str(save_location)

    # Demonstrate that encryption fails when only the global salt or
    # only the global passphrase are present among the site files.
    with pytest.raises(exceptions.GlobalCredentialsNotFound):
        secrets.encrypt(save_location_str, "pytest", "cicd")


@mock.patch.dict(
    os.environ, {
        'PEGLEG_PASSPHRASE': 'ytrr89erARAiPE34692iwUMvWqqBvC',
        'PEGLEG_SALT': 'MySecretSalt1234567890]['
    })
def test_get_global_creds(temp_deployment_files, tmpdir):
    # Create site files
    site_dir = tmpdir.join("deployment_files", "site", "cicd")

    # Create global passphrase and salt file
    with open(os.path.join(str(site_dir), 'secrets',
                           'passphrases',
                           'cicd-global-passphrase-encrypted.yaml'), "w") \
            as outfile:
        outfile.write(GLOBAL_PASSPHRASE_SALT_DOC)

    save_location = tmpdir.mkdir("encrypted_site_files")
    save_location_str = str(save_location)

    # Encrypt the global passphrase and salt file using site passphrase/salt
    secrets.encrypt(save_location_str, "pytest", "cicd")
    encrypted_files = listdir(save_location_str)
    assert len(encrypted_files) > 0

    # Capture global credentials, verify we have the right ones
    passphrase, salt = secrets.get_global_creds("cicd")
    assert passphrase.decode() == "TbKYNtM@3gXpL=AFLAwU?&Ey"
    assert salt.decode() == "h3=DQ#GNYEuCvybgpfW7ZxAP"


@mock.patch.dict(
    os.environ, {
        'PEGLEG_PASSPHRASE': 'ytrr89erARAiPE34692iwUMvWqqBvC',
        'PEGLEG_SALT': 'MySecretSalt1234567890]['
    })
def test_global_encrypt_decrypt(temp_deployment_files, tmpdir):
    # Create site files
    site_dir = tmpdir.join("deployment_files", "site", "cicd")

    # Create and encrypt global passphrase and salt file using site keys
    with open(os.path.join(str(site_dir), 'secrets',
                           'passphrases',
                           'cicd-global-passphrase-encrypted.yaml'), "w") \
            as outfile:
        outfile.write(GLOBAL_PASSPHRASE_SALT_DOC)

    save_location = tmpdir.mkdir("encrypted_site_files")
    save_location_str = str(save_location)

    # Encrypt the global passphrase and salt file using site passphrase/salt
    secrets.encrypt(save_location_str, "pytest", "cicd")

    # Create and encrypt a global type document
    global_doc_path = os.path.join(
        str(site_dir), 'secrets', 'passphrases', 'globally_encrypted_doc.yaml')
    with open(global_doc_path, "w") as outfile:
        outfile.write(TEST_GLOBAL_DATA)

    # encrypt documents and validate that they were encrypted
    doc_mgr = PeglegSecretManagement(
        file_path=global_doc_path, author='pytest', site_name='cicd')
    doc_mgr.encrypt_secrets(global_doc_path)
    doc = doc_mgr.documents[0]
    assert doc.is_encrypted()
    assert doc.data['encrypted']['by'] == 'pytest'

    doc_mgr = PeglegSecretManagement(
        file_path=global_doc_path, author='pytest', site_name='cicd')
    decrypted_data = doc_mgr.get_decrypted_secrets()
    test_data = list(yaml.safe_load_all(TEST_GLOBAL_DATA))
    assert test_data[0]['data'] == decrypted_data[0]['data']
    assert test_data[0]['schema'] == decrypted_data[0]['schema']

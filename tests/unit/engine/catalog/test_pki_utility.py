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

import json
import time

import click
import mock
import pytest

from pegleg import config
from pegleg.engine.catalog import pki_utility
from pegleg.engine.common import managed_document

CERT_HEADER = '-----BEGIN CERTIFICATE-----\n'
CERT_KEY_HEADER = '-----BEGIN RSA PRIVATE KEY-----\n'
PUBLIC_KEY_HEADER = '-----BEGIN PUBLIC KEY-----\n'
PRIVATE_KEY_HEADER = '-----BEGIN RSA PRIVATE KEY-----\n'

PEGLEG_MANAGED_DOC_SCHEMA = 'pegleg/PeglegManagedDocument/v1'
CA_SCHEMA = 'deckhand/CertificateAuthority/v1'
CA_KEY_SCHEMA = 'deckhand/CertificateAuthorityKey/v1'
CERT_SCHEMA = 'deckhand/Certificate/v1'
CERT_KEY_SCHEMA = 'deckhand/CertificateKey/v1'
PUBLIC_KEY_SCHEMA = 'deckhand/PublicKey/v1'
PRIVATE_KEY_SCHEMA = 'deckhand/PrivateKey/v1'


@pytest.mark.skipif(
    not pki_utility.PKIUtility.cfssl_exists(),
    reason='cfssl must be installed to execute these tests')
class TestPKIUtility(object):
    @classmethod
    def setup_class(cls):
        mock.patch.object(
            managed_document,
            '_get_repo_url_and_rev',
            new=lambda: ('fake://github.com/nothing.git', 'master')).start()

    def test_generate_ca(self):
        pki_obj = pki_utility.PKIUtility()
        ca_cert_wrapper, ca_key_wrapper = pki_obj.generate_ca(
            self.__class__.__name__)

        assert 'pegleg/PeglegManagedDocument/v1' == ca_cert_wrapper['schema']
        assert 'pegleg/PeglegManagedDocument/v1' == ca_key_wrapper['schema']

        ca_cert = ca_cert_wrapper['data']['managedDocument']
        assert isinstance(ca_cert, dict), ca_cert
        ca_key = ca_key_wrapper['data']['managedDocument']
        assert isinstance(ca_key, dict), ca_key

        assert isinstance(ca_cert, dict), ca_cert
        assert CA_SCHEMA in ca_cert['schema']
        assert CERT_HEADER in ca_cert['data']

        assert isinstance(ca_key, dict), ca_key
        assert CA_KEY_SCHEMA in ca_key['schema']
        assert CERT_KEY_HEADER in ca_key['data']

    def test_generate_keypair(self):
        pki_obj = pki_utility.PKIUtility()
        pub_key_wrapper, priv_key_wrapper = pki_obj.generate_keypair(
            self.__class__.__name__)

        assert 'pegleg/PeglegManagedDocument/v1' == pub_key_wrapper['schema']
        assert 'pegleg/PeglegManagedDocument/v1' == priv_key_wrapper['schema']

        pub_key = pub_key_wrapper['data']['managedDocument']
        assert isinstance(pub_key, dict), pub_key
        priv_key = priv_key_wrapper['data']['managedDocument']
        assert isinstance(pub_key, dict), priv_key

        assert isinstance(pub_key, dict), pub_key
        assert PUBLIC_KEY_SCHEMA in pub_key['schema']
        assert PUBLIC_KEY_HEADER in pub_key['data']

        assert isinstance(priv_key, dict), priv_key
        assert PRIVATE_KEY_SCHEMA in priv_key['schema']
        assert PRIVATE_KEY_HEADER in priv_key['data']

    def test_generate_certificate(self):
        pki_obj = pki_utility.PKIUtility(duration=365)
        ca_cert_wrapper, ca_key_wrapper = pki_obj.generate_ca(
            self.__class__.__name__)
        ca_cert = ca_cert_wrapper['data']['managedDocument']
        ca_key = ca_key_wrapper['data']['managedDocument']

        cert_wrapper, cert_key_wrapper = pki_obj.generate_certificate(
            name=self.__class__.__name__,
            ca_cert=ca_cert['data'],
            ca_key=ca_key['data'],
            cn='admin')

        assert 'pegleg/PeglegManagedDocument/v1' == cert_wrapper['schema']
        assert 'pegleg/PeglegManagedDocument/v1' == cert_key_wrapper['schema']

        cert = cert_wrapper['data']['managedDocument']
        assert isinstance(cert, dict), cert
        cert_key = cert_key_wrapper['data']['managedDocument']
        assert isinstance(cert_key, dict), cert_key

        assert isinstance(cert, dict), cert
        assert CERT_SCHEMA in cert['schema']
        assert CERT_HEADER in cert['data']

        assert isinstance(cert_key, dict), cert_key
        assert CERT_KEY_SCHEMA in cert_key['schema']
        assert CERT_KEY_HEADER in cert_key['data']

    def test_check_expiry_is_expired_false(self):
        """Check that ``check_expiry`` returns False if cert isn't expired."""
        pki_obj = pki_utility.PKIUtility(duration=0)

        ca_config = json.loads(pki_obj.ca_config)
        ca_config['signing']['default']['expiry'] = '1h'

        m_callable = mock.PropertyMock(return_value=json.dumps(ca_config))
        with mock.patch.object(pki_utility.PKIUtility, 'ca_config',
                               new_callable=m_callable):
            ca_cert_wrapper, ca_key_wrapper = pki_obj.generate_ca(
                self.__class__.__name__)
            ca_cert = ca_cert_wrapper['data']['managedDocument']
            ca_key = ca_key_wrapper['data']['managedDocument']
            cert_wrapper, _ = pki_obj.generate_certificate(
                name=self.__class__.__name__,
                ca_cert=ca_cert['data'],
                ca_key=ca_key['data'],
                cn='admin')
        cert = cert_wrapper['data']['managedDocument']

        # Validate that the cert hasn't expired.
        is_expired = pki_obj.check_expiry(cert=cert['data'])['expired']
        assert not is_expired

    def test_check_expiry_is_expired_true(self):
        """Check that ``check_expiry`` returns True is cert is expired.

        Second values are used to demonstrate precision down to the second.
        """
        pki_obj = pki_utility.PKIUtility(duration=0)

        ca_config = json.loads(pki_obj.ca_config)
        ca_config['signing']['default']['expiry'] = '1s'

        m_callable = mock.PropertyMock(return_value=json.dumps(ca_config))
        with mock.patch.object(pki_utility.PKIUtility, 'ca_config',
                               new_callable=m_callable):
            ca_cert_wrapper, ca_key_wrapper = pki_obj.generate_ca(
                self.__class__.__name__)
            ca_cert = ca_cert_wrapper['data']['managedDocument']
            ca_key = ca_key_wrapper['data']['managedDocument']
            cert_wrapper, _ = pki_obj.generate_certificate(
                name=self.__class__.__name__,
                ca_cert=ca_cert['data'],
                ca_key=ca_key['data'],
                cn='admin')
        cert = cert_wrapper['data']['managedDocument']

        time.sleep(2)

        # Validate that the cert has expired.
        is_expired = pki_obj.check_expiry(cert=cert['data'])['expired']
        assert is_expired

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

import datetime
import json
import logging
import os
# Ignore bandit false positive: B404:blacklist
# The purpose of this module is to safely encapsulate calls via fork.
import subprocess  # nosec
import tempfile

from dateutil import parser
import pytz
import yaml

from pegleg.engine import exceptions
from pegleg.engine.util.pegleg_managed_document import \
    PeglegManagedSecretsDocument

LOG = logging.getLogger(__name__)

__all__ = ['PKIUtility']


# TODO(felipemonteiro): Create an abstract base class for other future Catalog
# classes.


class PKIUtility(object):
    """Public Key Infrastructure utility class.

    Responsible for generating certificate and CA documents using ``cfssl`` and
    keypairs using ``openssl``. These secrets are all wrapped in instances
    of ``pegleg/PeglegManagedDocument/v1``.

    """

    @staticmethod
    def cfssl_exists():
        """Checks whether cfssl command exists. Useful for testing."""
        try:
            subprocess.check_output(  # nosec
                ['which', 'cfssl'], stderr=subprocess.STDOUT)
            return True
        except subprocess.CalledProcessError:
            return False

    def __init__(self, *, block_strings=True, duration=None):
        self.block_strings = block_strings
        self._ca_config_string = None
        self.duration = duration

    @property
    def ca_config(self):
        if self.duration is None or self.duration < 0:
            raise exceptions.PKICertificateInvalidDuration()

        if not self._ca_config_string:
            self._ca_config_string = json.dumps({
                'signing': {
                    'default': {
                        'expiry':
                            str(24 * self.duration) + 'h',
                        'usages': [
                            'signing', 'key encipherment', 'server auth',
                            'client auth'],
                    },
                },
            })
        return self._ca_config_string

    def generate_ca(self, ca_name):
        """Generate CA cert and associated key.

        :param str ca_name: Name of Certificate Authority in wrapped document.
        :returns: Tuple of (wrapped CA cert, wrapped CA key)
        :rtype: tuple[dict, dict]

        """

        result = self._cfssl(
            ['gencert', '-initca', 'csr.json'],
            files={
                'csr.json': self.csr(name=ca_name),
            })

        return (self._wrap_ca(ca_name, result['cert']),
                self._wrap_ca_key(ca_name, result['key']))

    def generate_keypair(self, name):
        """Generate keypair.

        :param str name: Name of keypair in wrapped document.
        :returns: Tuple of (wrapped public key, wrapped private key)
        :rtype: tuple[dict, dict]

        """

        priv_result = self._openssl(['genrsa', '-out', 'priv.pem'])
        pub_result = self._openssl(
            ['rsa', '-in', 'priv.pem', '-pubout', '-out', 'pub.pem'],
            files={
                'priv.pem': priv_result['priv.pem'],
            })

        return (self._wrap_pub_key(name, pub_result['pub.pem']),
                self._wrap_priv_key(name, priv_result['priv.pem']))

    def generate_certificate(self,
                             name,
                             *,
                             ca_cert,
                             ca_key,
                             cn,
                             groups=None,
                             hosts=None):
        """Generate certificate and associated key given CA cert and key.

        :param str name: Name of certificate in wrapped document.
        :param str ca_cert: CA certificate.
        :param str ca_key: CA certificate key.
        :param str cn: Common name associated with certificate.
        :param list groups: List of groups associated with certificate.
        :param list hosts: List of hosts associated with certificate.
        :returns: Tuple of (wrapped certificate, wrapped certificate key)
        :rtype: tuple[dict, dict]

        """

        if groups is None:
            groups = []
        if hosts is None:
            hosts = []

        result = self._cfssl(
            [
                'gencert', '-ca', 'ca.pem', '-ca-key', 'ca-key.pem', '-config',
                'ca-config.json', 'csr.json'
            ],
            files={
                'ca-config.json': self.ca_config,
                'ca.pem': ca_cert,
                'ca-key.pem': ca_key,
                'csr.json': self.csr(name=cn, groups=groups, hosts=hosts),
            })

        return (self._wrap_cert(name, result['cert']),
                self._wrap_cert_key(name, result['key']))

    def csr(self,
            *,
            name,
            groups=None,
            hosts=None,
            key={
                'algo': 'rsa',
                'size': 2048
            }):
        if groups is None:
            groups = []
        if hosts is None:
            hosts = []

        return json.dumps({
            'CN': name,
            'key': key,
            'hosts': hosts,
            'names': [{
                'O': g
            } for g in groups],
        })

    def cert_info(self, cert):
        """Retrieve certificate info via ``cfssl``.

        :param str cert: Client certificate that contains the public key.
        :returns: Information related to certificate.
        :rtype: dict

        """

        return self._cfssl(
            ['certinfo', '-cert', 'cert.pem'], files={
                'cert.pem': cert,
            })

    def check_expiry(self, cert):
        """Chek whether a given certificate is expired.

        :param str cert: Client certificate that contains the public key.
        :returns: In dictionary format returns the expiration date of the cert
            and True if the cert is or will be expired within the next
            expire_in_days
        :rtype: dict

        """

        if self.duration is None or self.duration < 0:
            raise exceptions.PKICertificateInvalidDuration()

        info = self.cert_info(cert)
        expiry_str = info['not_after']
        expiry = parser.parse(expiry_str)
        # expiry is timezone-aware; do the same for `now`.
        expiry_window = pytz.utc.localize(datetime.datetime.utcnow()) + \
            datetime.timedelta(days=self.duration)
        expired = expiry_window > expiry
        expiry = expiry.strftime('%d-%b-%Y %H:%M:%S %Z')
        return {'expiry_date': expiry, 'expired': expired}

    def _cfssl(self, command, *, files=None):
        """Executes ``cfssl`` command via ``subprocess`` call."""
        if not files:
            files = {}
        with tempfile.TemporaryDirectory() as tmp:
            for filename, data in files.items():
                with open(os.path.join(tmp, filename), 'w') as f:
                    f.write(data)

            # Ignore bandit false positive:
            #   B603:subprocess_without_shell_equals_true
            # This method wraps cfssl calls originating from this module.
            result = subprocess.check_output(  # nosec
                ['cfssl'] + command, cwd=tmp, stderr=subprocess.PIPE)
            if not isinstance(result, str):
                result = result.decode('utf-8')
            return json.loads(result)

    def _openssl(self, command, *, files=None):
        """Executes ``openssl`` command via ``subprocess`` call."""
        if not files:
            files = {}

        with tempfile.TemporaryDirectory() as tmp:
            for filename, data in files.items():
                with open(os.path.join(tmp, filename), 'w') as f:
                    f.write(data)

            # Ignore bandit false positive:
            #   B603:subprocess_without_shell_equals_true
            # This method wraps openssl calls originating from this module.
            subprocess.check_call(  # nosec
                ['openssl'] + command,
                cwd=tmp,
                stderr=subprocess.PIPE)

            result = {}
            for filename in os.listdir(tmp):
                if filename not in files:
                    with open(os.path.join(tmp, filename)) as f:
                        result[filename] = f.read()

            return result

    def _wrap_ca(self, name, data):
        return self.wrap_document(kind='CertificateAuthority', name=name,
                                  data=data, block_strings=self.block_strings)

    def _wrap_ca_key(self, name, data):
        return self.wrap_document(kind='CertificateAuthorityKey', name=name,
                                  data=data, block_strings=self.block_strings)

    def _wrap_cert(self, name, data):
        return self.wrap_document(kind='Certificate', name=name, data=data,
                                  block_strings=self.block_strings)

    def _wrap_cert_key(self, name, data):
        return self.wrap_document(kind='CertificateKey', name=name, data=data,
                                  block_strings=self.block_strings)

    def _wrap_priv_key(self, name, data):
        return self.wrap_document(kind='PrivateKey', name=name, data=data,
                                  block_strings=self.block_strings)

    def _wrap_pub_key(self, name, data):
        return self.wrap_document(kind='PublicKey', name=name, data=data,
                                  block_strings=self.block_strings)

    @staticmethod
    def wrap_document(kind, name, data, block_strings=True):
        """Wrap document ``data`` with PeglegManagedDocument pattern.

        :param str kind: The kind of document (found in ``schema``).
        :param str name: Name of the document.
        :param dict data: Document data.
        :param bool block_strings: Whether to dump out certificate data as
            block-style YAML string. Defaults to true.
        :return: the wrapped document
        :rtype: dict
        """

        wrapped_schema = 'deckhand/%s/v1' % kind
        wrapped_metadata = {
            'schema': 'metadata/Document/v1',
            'name': name,
            'layeringDefinition': {
                'abstract': False,
                'layer': 'site',
            },
            'storagePolicy': 'cleartext'
        }
        wrapped_data = PKIUtility._block_literal(
            data, block_strings=block_strings)

        document = {
            "schema": wrapped_schema,
            "metadata": wrapped_metadata,
            "data": wrapped_data
        }

        return PeglegManagedSecretsDocument(document).pegleg_document

    @staticmethod
    def _block_literal(data, block_strings=True):
        if block_strings:
            return block_literal(data)
        else:
            return data


class block_literal(str):
    pass


def block_literal_representer(dumper, data):
    return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='|')


yaml.add_representer(block_literal, block_literal_representer)

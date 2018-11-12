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
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from cryptography.exceptions import InvalidSignature

KEY_LENGTH = 32
ITERATIONS = 10000
LOG = logging.getLogger(__name__)


def encrypt(unencrypted_data,
            passphrase,
            salt,
            key_length=KEY_LENGTH,
            iterations=ITERATIONS):
    """
    Encrypt the data, using the provided passphrase and salt,
    and return the encrypted data.

    :param unencrypted_data: Secret data to encrypt
    :type unencrypted_data: bytes
    :param passphrase: Passphrase to use to generate encryption key. Must be
    at least 24-byte long
    :type passphrase: bytes
    :param salt: salt to use to generate encryption key. Must be randomly
    generated.
    :type salt: bytes
    :param key_length: Length of the encryption key to generate, in bytes.
    Will default to 32, if not provided.
    :type key_length: positive integer.
    :param iterations: A large number, used as seed to increase the entropy
    in randomness of the generated key for encryption, and hence greatly
    increase the security of encrypted data. will default to 10000, if not
    provided.
    :type iterations: positive integer.
    :return: Encrypted secret data
    :rtype: bytes
    """

    return Fernet(_generate_key(passphrase, salt, key_length,
                                iterations)).encrypt(unencrypted_data)


def decrypt(encrypted_data,
            passphrase,
            salt,
            key_length=KEY_LENGTH,
            iterations=ITERATIONS):
    """
    Decrypt the data, using the provided passphrase and salt,
    and return the decrypted data.

    :param encrypted_data: Encrypted secret data
    :type encrypted_data: bytes
    :param passphrase: Passphrase to use to generate decryption key. Must be
    at least 32-byte long.
    :type passphrase: bytes
    :param salt: salt to use to generate decryption key. Must be randomly
    generated.
    :type salt: bytes
    :param key_length: Length of the decryption key to generate, in bytes.
    will default to 32, if not provided.
    :type key_length: positive integer.
    :param iterations: A large number, used as seed to increase entropy in
    the randomness of the generated key for decryption, and hence greatly
    increase the security of encrypted data. Will default to 10000, if not
    provided.
    :type iterations: positive integer.
    :return: Decrypted secret data
    :rtype: bytes
    :raises InvalidSignature: If the provided passphrase, and/or
    salt does not match the values used to encrypt the data.
    """

    try:
        return Fernet(_generate_key(passphrase, salt, key_length,
                                    iterations)).decrypt(encrypted_data)
    except InvalidSignature:
        LOG.error('Signature verification to decrypt secrets failed. Please '
                  'check your provided passphrase and salt and try again.')
        raise


def _generate_key(passphrase, salt, key_length, iterations):
    """
    Use the passphrase and salt and PBKDF2HMAC key derivation algorithm,
    to generate and return a Fernet key to be used for encryption and
    decryption of secret data.

    :param passphrase: Passphrase to use to generate decryption key. Must be
    at least 24-byte long.
    :type passphrase: bytes
    :param salt: salt to use to generate decryption key. Must be randomly
    generated.
    :type salt: bytes
    :param key_length: Length of the decryption key to generate, in bytes.
    Will default to 32, if not provided.
    :type key_length: positive integer.
    :param iterations: A large number, used as seed to increase the entropy
    of the randomness of the generated key. will default to 10000, if not
    provided.
    :type iterations: positive integer.
    :return: base64 encoded, URL safe Fernet key for encryption or decryption
    """

    kdf = PBKDF2HMAC(
        algorithm=hashes.SHA256(),
        length=key_length,
        salt=salt,
        iterations=iterations,
        backend=default_backend())
    return base64.urlsafe_b64encode(kdf.derive(passphrase))

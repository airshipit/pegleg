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

import random
import string

from pegleg.engine.catalogs import passphrase_profiles
from pegleg.engine import exceptions

__all__ = ['CryptoString']


class CryptoString(object):
    def __init__(self, profile=None):
        if profile and profile.lower() in passphrase_profiles.VALID_PROFILES:
            self._pool = passphrase_profiles.PROFILES[profile.lower()]
        elif profile:
            raise exceptions.InvalidPassphraseProfile(
                pprofile=profile.lower(),
                validvalues=passphrase_profiles.VALID_PROFILES)
        else:
            self._pool = passphrase_profiles.PROFILES['default']
        self._random = random.SystemRandom()
        self.determine_char_sets()

    def determine_char_sets(self):
        self.test_upper = self.has_upper(self._pool)
        self.test_lower = self.has_lower(self._pool)
        self.test_number = self.has_number(self._pool)
        self.test_symbol = self.has_symbol(self._pool)

    def has_upper(self, crypto_str):
        """Check if string contains an uppercase letter

        :param str crypto_str: The string to test.
        :returns: True if string contains at least one uppercase letter.
        :rtype: boolean
        """

        return any(char in string.ascii_uppercase for char in crypto_str)

    def has_lower(self, crypto_str):
        """Check if string contains a lowercase letter

        :param str crypto_str: The string to test.
        :returns: True if string contains at least one lowercase letter.
        :rtype: boolean
        """

        return any(char in string.ascii_lowercase for char in crypto_str)

    def has_number(self, crypto_str):
        """Check if string contains a number

        :param str crypto_str: The string to test.
        :returns: True if string contains at least one number.
        :rtype: boolean
        """

        return any(char in string.digits for char in crypto_str)

    def has_symbol(self, crypto_str):
        """Check if string contains a symbol

        :param str crypto_str: The string to test.
        :returns: True if string contains at least one symbol.
        :rtype: boolean
        """

        return any(char in string.punctuation for char in crypto_str)

    def validate_crypto_str(self, crypto_str):
        """Ensure cryptostring contains characters from all sets

        :param str crypto_str: The string to test.
        :returns: True if string contains at least one each: uppercase letter,
            lowercase letter, number and symbol if that character set is
            present in the original passphrase pool.
        :rtype: boolean
        """

        test_cases = [
            self.test_upper, self.test_lower, self.test_number,
            self.test_symbol
        ]
        tests = [
            self.has_upper, self.has_lower, self.has_number, self.has_symbol
        ]
        for (test_case, test) in zip(test_cases, tests):
            if test_case and not test(crypto_str):
                return False

        return True

    def get_crypto_string(self, length=24):
        """Create and return a random cryptographic string.

        When the string is generated, it will be checked to determine if it
        contains uppercase letters, lowercase letters, numbers and symbols.
        If it does not contain at least one character from each set it will
        be re-generated until it does.

        :param int length: Length of crypto string to generate. If this length
            is smaller than 24, or not defined, the length will default to 24.
        :returns: The generated cryptographic string
        :rtype: string
        """

        while True:
            crypto_str = ''.join(
                self._random.choice(self._pool)
                for _ in range(max(24, length)))
            if self.validate_crypto_str(crypto_str):
                break

        return crypto_str

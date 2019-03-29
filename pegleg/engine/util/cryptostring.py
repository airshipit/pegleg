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

__all__ = ['CryptoString']


class CryptoString(object):

    def __init__(self):
        punctuation = '@#&-+=?'
        self._pool = string.ascii_letters + string.digits + punctuation
        self._random = random.SystemRandom()

    def get_crypto_string(self, length=24):
        """
        Create and return a random cryptographic string of length ``length``.
        """
        return ''.join(self._random.choice(self._pool)
                       for _ in range(max(24, length)))

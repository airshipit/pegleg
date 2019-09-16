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

from pegleg.engine.util.cryptostring import CryptoString


def test_cryptostring_default_len():
    s_util = CryptoString()
    s = s_util.get_crypto_string()
    assert len(s) == 24


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


def test_cryptostring_has_upper():
    s_util = CryptoString()
    crypto_string = 'Th1sP@sswordH4sUppers!'
    assert s_util.has_upper(crypto_string) is True
    crypto_string = 'THISPASSWORDHASONLYUPPERS'
    assert s_util.has_upper(crypto_string) is True
    crypto_string = 'th1sp@sswordh4snouppers!'
    assert s_util.has_upper(crypto_string) is False


def test_cryptostring_has_lower():
    s_util = CryptoString()
    crypto_string = 'Th1sP@sswordH4sLowers!'
    assert s_util.has_lower(crypto_string) is True
    crypto_string = 'thispasswordhasonlylowers'
    assert s_util.has_lower(crypto_string) is True
    crypto_string = 'TH1SP@SSWORDH4SNOLOWERS!'
    assert s_util.has_lower(crypto_string) is False


def test_cryptostring_has_number():
    s_util = CryptoString()
    crypto_string = 'Th1sP@sswordH4sNumbers!'
    assert s_util.has_number(crypto_string) is True
    crypto_string = '123456789012345678901234567890'
    assert s_util.has_number(crypto_string) is True
    crypto_string = 'ThisP@sswordHasNoNumbers!'
    assert s_util.has_number(crypto_string) is False


def test_cryptostring_has_symbol():
    s_util = CryptoString()
    crypto_string = 'Th1sP@sswordH4sSymbols!'
    assert s_util.has_symbol(crypto_string) is True
    crypto_string = r'!@#$%^&*()[]\}{|<>?,./~`'
    assert s_util.has_symbol(crypto_string) is True
    crypto_string = 'ThisPasswordH4sNoSymbols'
    assert s_util.has_symbol(crypto_string) is False


def test_cryptostring_has_all():
    s_util = CryptoString()
    crypto_string = s_util.get_crypto_string()
    assert s_util.validate_crypto_str(crypto_string) is True
    crypto_string = 'Th1sP@sswordH4sItAll!'
    assert s_util.validate_crypto_str(crypto_string) is True
    crypto_string = 'th1sp@sswordh4snouppers!'
    assert s_util.validate_crypto_str(crypto_string) is False
    crypto_string = 'TH1SP@SSWORDH4SNOLOWERS!'
    assert s_util.validate_crypto_str(crypto_string) is False
    crypto_string = 'ThisP@sswordHasNoNumbers!'
    assert s_util.validate_crypto_str(crypto_string) is False
    crypto_string = 'ThisPasswordH4sNoSymbols'
    assert s_util.validate_crypto_str(crypto_string) is False


def test_cryptostring_default_profile():
    s_util = CryptoString(profile='default')
    crypto_string = s_util.get_crypto_string()
    assert s_util.has_lower(crypto_string) is True
    assert s_util.has_upper(crypto_string) is True
    assert s_util.has_number(crypto_string) is True
    assert s_util.has_symbol(crypto_string) is True
    bad_symbols = any(
        char in '!"$%()*,./:;<>[]^_`{|}~\'' for char in crypto_string)
    assert not bad_symbols


def test_cryptostring_alphanumeric_profile():
    s_util = CryptoString(profile='alphanumeric')
    crypto_string = s_util.get_crypto_string()
    assert s_util.has_lower(crypto_string) is True
    assert s_util.has_upper(crypto_string) is True
    assert s_util.has_number(crypto_string) is True
    assert s_util.has_symbol(crypto_string) is False


def test_cryptostring_alphanumeric_lower_profile():
    s_util = CryptoString(profile='alphanumeric_lower')
    crypto_string = s_util.get_crypto_string()
    assert s_util.has_lower(crypto_string) is True
    assert s_util.has_upper(crypto_string) is False
    assert s_util.has_number(crypto_string) is True
    assert s_util.has_symbol(crypto_string) is False


def test_cryptostring_alphanumeric_upper_profile():
    s_util = CryptoString(profile='alphanumeric_upper')
    crypto_string = s_util.get_crypto_string()
    assert s_util.has_lower(crypto_string) is False
    assert s_util.has_upper(crypto_string) is True
    assert s_util.has_number(crypto_string) is True
    assert s_util.has_symbol(crypto_string) is False


def test_cryptostring_all_profile():
    s_util = CryptoString(profile='all')
    crypto_string = s_util.get_crypto_string()
    assert s_util.has_lower(crypto_string) is True
    assert s_util.has_upper(crypto_string) is True
    assert s_util.has_number(crypto_string) is True
    assert s_util.has_symbol(crypto_string) is True


def test_cryptostring_hex_lower_profile():
    s_util = CryptoString(profile='hex_lower')
    crypto_string = s_util.get_crypto_string()
    assert s_util.has_lower(crypto_string) is True
    assert s_util.has_upper(crypto_string) is False
    assert s_util.has_number(crypto_string) is True
    assert s_util.has_symbol(crypto_string) is False
    bad_letters = any(char in 'ghijklmnopqrstuvwxyz' for char in crypto_string)
    assert not bad_letters


def test_cryptostring_hex_upper_profile():
    s_util = CryptoString(profile='hex_upper')
    crypto_string = s_util.get_crypto_string()
    assert s_util.has_lower(crypto_string) is False
    assert s_util.has_upper(crypto_string) is True
    assert s_util.has_number(crypto_string) is True
    assert s_util.has_symbol(crypto_string) is False
    bad_letters = any(char in 'GHIJKLMNOPQRSTUVWXYZ' for char in crypto_string)
    assert not bad_letters

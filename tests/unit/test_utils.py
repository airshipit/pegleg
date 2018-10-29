# Copyright 2010 United States Government as represented by the
# Administrator of the National Aeronautics and Space Administration.
# Copyright 2015 Hewlett-Packard Development Company, L.P.
# Copyright 2017 AT&T Intellectual Property.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import os
import random
import requests
import uuid

_PROXY_SERVERS = {
    'http':
    os.getenv('HTTP_PROXY', os.getenv('http_proxy',
                                      'http://proxy.example.com')),
    'https':
    os.getenv('HTTPS_PROXY',
              os.getenv('https_proxy', 'https://proxy.example.com'))
}


def rand_name(name='', prefix='pegleg'):
    """Generate a random name that includes a random number

    :param str name: The name that you want to include
    :param str prefix: The prefix that you want to include
    :return: a random name. The format is
             '<prefix>-<name>-<random number>'.
             (e.g. 'prefixfoo-namebar-154876201')
    :rtype: string
    """
    randbits = str(random.randint(1, 0x7fffffff))
    rand_name = randbits
    if name:
        rand_name = name + '-' + rand_name
    if prefix:
        rand_name = prefix + '-' + rand_name
    return rand_name


def is_connected():
    """Verifies whether network connectivity is up.

    :returns: True if connected else False.
    """
    try:
        r = requests.get("http://www.github.com/", proxies={}, timeout=3)
        return r.ok
    except requests.exceptions.RequestException:
        return False


def is_connected_behind_proxy():
    """Verifies whether network connectivity is up behind given proxy.

    :returns: True if connected else False.
    """
    try:
        r = requests.get(
            "http://www.github.com/", proxies=_PROXY_SERVERS, timeout=3)
        return r.ok
    except requests.exceptions.RequestException:
        return False

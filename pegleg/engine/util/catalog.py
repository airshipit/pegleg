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
"""Utility functions for catalog files such as pki-catalog.yaml."""

import logging

from pegleg.engine.util import definition

LOG = logging.getLogger(__name__)

__all__ = ('iterate', 'decode_bytes')


def decode_bytes(obj):
    """If the argument is bytes, decode it.

    :param Object obj: A string or byte object
    :return: A string representation of obj
    :rtype: str

    """
    if isinstance(obj, bytes):
        return obj.decode('utf-8')
    elif isinstance(obj, str):
        return obj
    else:
        raise ValueError("ERROR: {} is not bytes or a string.".format(obj))


def iterate(kind, sitename=None, documents=None):
    """Retrieve the list of catalog documents by catalog schema ``kind``.

    :param str kind: The schema kind of the catalog. For example, for schema
        ``pegleg/PKICatalog/v1`` kind should be "PKICatalog".
    :param str sitename: (optional) Site name for retrieving documents.
        Multually exclusive with ``documents``.
    :param str documents: (optional) Documents to search through. Mutually
        exclusive with ``sitename``.
    :return: All catalog documents for ``kind``.
    :rtype: generator[dict]

    """

    if not any([sitename, documents]):
        raise ValueError('Either `sitename` or `documents` must be specified')

    documents = documents or definition.documents_for_site(sitename)
    for document in documents:
        schema = document.get('schema')
        # TODO(felipemonteiro): Remove 'promenade/%s/v1' once site manifest
        # documents switch to new 'pegleg' namespace.
        if schema == 'pegleg/%s/v1' % kind:
            yield document
        elif schema == 'promenade/%s/v1' % kind:
            LOG.warning('The schema promenade/%s/v1 is deprecated. Use '
                        'pegleg/%s/v1 instead.', kind, kind)
            yield document

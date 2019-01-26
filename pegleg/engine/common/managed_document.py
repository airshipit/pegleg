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

from pegleg import config
from pegleg.engine.util import git

MANAGED_DOCUMENT_SCHEMA = 'pegleg/PeglegManagedDocument/v1'
SUPPORTED_SCHEMAS = (
    'deckhand/CertificateAuthority/v1',
    'deckhand/CertificateAuthorityKey/v1',
    'deckhand/Certificate/v1',
    'deckhand/CertificateKey/v1',
    'deckhand/PublicKey/v1',
    'deckhand/PrivateKey/v1',
)

_KIND_TO_PATH = {
    'CertificateAuthority': 'certificates',
    'CertificateAuthorityKey': 'certificates',
    'Certificate': 'certificates',
    'CertificateKey': 'certificates',
    'PublicKey': 'keypairs',
    'PrivateKey': 'keypairs'
}


def is_managed_document(document):
    """Utility for determining whether a document is wrapped by
    ``pegleg/PeglegManagedDocument/v1`` pattern.

    :param dict document: Document to check.
    :returns: True if document is managed, else False.
    :rtype: bool

    """

    return document.get('schema') == "pegleg/PeglegManagedDocument/v1"


def get_document_path(sitename, wrapper_document, cert_to_ca_map=None):
    """Get path for outputting generated certificates or keys to.

    Also updates the provenance path (``data.generated.specifiedBy.path``)
    for ``wrapper_document``.

    * Certificates ar written to: ``<site>/secrets/certificates``
    * Keypairs are written to: ``<site>/secrets/keypairs``
    * Passphrases are written to: ``<site>/secrets/passphrases``

    * The generated filenames for passphrases will follow the pattern
      ``<passphrase-doc-name>.yaml``.
    * The generated filenames for certificate authorities will follow the
      pattern ``<ca-name>_ca.yaml``.
    * The generated filenames for certificates will follow the pattern
      ``<ca-name>_<certificate-doc-name>_certificate.yaml``.
    * The generated filenames for certificate keys will follow the pattern
      ``<ca-name>_<certificate-doc-name>_key.yaml``.
    * The generated filenames for keypairs will follow the pattern
      ``<keypair-doc-name>.yaml``.

    :param str sitename: Name of site.
    :param dict wrapper_document: Generated ``PeglegManagedDocument``.
    :param dict cert_to_ca_map: Dict that maps certificate names to
        their respective CA name.
    :returns: Path to write document out to.
    :rtype: str

    """

    cert_to_ca_map = cert_to_ca_map or {}

    managed_document = wrapper_document['data']['managedDocument']
    kind = managed_document['schema'].split("/")[1]
    name = managed_document['metadata']['name']

    path = "%s/secrets/%s" % (sitename, _KIND_TO_PATH[kind])

    if 'authority' in kind.lower():
        filename_structure = '%s_ca.yaml'
    elif 'certificate' in kind.lower():
        ca_name = cert_to_ca_map[name]
        filename_structure = ca_name + '_%s_certificate.yaml'
    elif 'public' in kind.lower() or 'private' in kind.lower():
        filename_structure = '%s.yaml'

    # Dashes in the document names are converted to underscores for
    # consistency.
    filename = (filename_structure % name).replace('-', '_')
    fullpath = os.path.join(path, filename)

    # Not all managed documents are generated. Only update path provenance
    # information for those that are.
    if wrapper_document['data'].get('generated'):
        wrapper_document['data']['generated']['specifiedBy']['path'] = fullpath
    return fullpath


def _get_repo_url_and_rev():
    repo_path_or_url = config.get_site_repo()
    repo_url = git.repo_url(repo_path_or_url)
    repo_rev = config.get_site_rev()
    return repo_url, repo_rev

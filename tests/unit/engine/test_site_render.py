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

import copy
import os
import shutil
import textwrap

import pytest
import yaml

from pegleg import config
from pegleg.engine import site
from pegleg.engine.util import files

_SITE_TEST_STRUCTURE = {
    'directories': {
        'secrets': {
            'directories': {
                'passphrases': {
                    'files': {}
                },
            },
        },
    },
    'files': {}
}

_SITE_DEFINITION = textwrap.dedent(
    """
    ---
    schema: pegleg/SiteDefinition/v1
    metadata:
      layeringDefinition: {abstract: false, layer: site}
      name: %(sitename)s
      schema: metadata/Document/v1
      storagePolicy: cleartext
    data:
      repositories:
        global:
          revision: v1.0
          url: http://nowhere.com
      site_type: %(sitename)s
    ...
    """)

_LAYERING_DEFINITION = textwrap.dedent(
    """
    ---
    schema: deckhand/LayeringPolicy/v1
    metadata:
      schema: metadata/Control/v1
      name: layering-policy
    data:
      layerOrder:
        - site
    """)

_PLAINTEXT_SECRET = textwrap.dedent(
    """
    ---
    schema: deckhand/Passphrase/v1
    metadata:
      schema: metadata/Document/v1
      name: plaintext-secret
      layeringDefinition:
        abstract: false
        layer: site
      storagePolicy: cleartext
    data: dde25e24d263e476cdcd
    ...
    """)

_MANAGED_SECRET = textwrap.dedent(
    """
    ---
    schema: pegleg/PeglegManagedDocument/v1
    metadata:
      name: managed-secret
      schema: metadata/Document/v1
      labels: {}
      layeringDefinition:
        abstract: false
        layer: site
      storagePolicy: cleartext
    data:
      managedDocument:
        schema: deckhand/Certificate/v1
        metadata:
          layeringDefinition:
            abstract: false
            layer: site
          name: managed-secret
          schema: metadata/Document/v1
          storagePolicy: cleartext
        data: |
          -----BEGIN CERTIFICATE-----
          MIIDSDCCAjCgAwIBAgIUaAjhb47nDilYQacmkdtprW42gHowDQYJKoZIhvcNAQEL
          BQAwKjETMBEGA1UEChMKS3ViZXJuZXRlczETMBEGA1UEAxMKa3ViZXJuZXRlczAe
          Fw0xOTA3MTEyMjQ4MDBaFw0yNDA3MDkyMjQ4MDBaMCoxEzARBgNVBAoTCkt1YmVy
          bmV0ZXMxEzARBgNVBAMTCmt1YmVybmV0ZXMwggEiMA0GCSqGSIb3DQEBAQUAA4IB
          DwAwggEKAoIBAQDVi4YbTvjC+txSiclIJpJGE7YQe9t2nOfEyBykIwbi70GgcVyR
          vNVN4bXQglG5EOVOv/A6DPQ3VIB4OsidPigwR7p8CCNl9yzVDSnhFtdcDv/Xw0z2
          aBjvOMS1cBj9QzJIE04vct1sH1BQQ2l3PyOXtOalj1URFm+RLm2Lj+JiCnaxIV3g
          Rp+CtiyYWwwfW+3GbDJGuXjIlch6zHa3BynoqvZBbWvMQ1hUn/iBKUtxtfHNDtoz
          Xn5S6Cxzz2l7XaHtotKtlHwkH+U701nvj8vLev0EgDcESbl6yGqgHJIL6UieQlXL
          4uKm8r9ThIhUuGBnDieydZNuVNpIPRVFeb0jAgMBAAGjZjBkMA4GA1UdDwEB/wQE
          AwIBBjASBgNVHRMBAf8ECDAGAQH/AgECMB0GA1UdDgQWBBS7TMynvzvifS00ysY9
          TGwjdejl3DAfBgNVHSMEGDAWgBS7TMynvzvifS00ysY9TGwjdejl3DANBgkqhkiG
          9w0BAQsFAAOCAQEAglQGmrNz+BDq2CKq68JSGXhi5PCZ1NwmJmQekI+8jdV8Hd7g
          urnoZGoMk1i7ZiL8YiOkiZNNWolKSF5whH/COBVBtTkYaPhCKfMDOi2sIVftv0q8
          jkCIajudTCdf2ZcxB6/T+5wVUipjHtYzylTEaBhg171jc9P9vinSK6WSI6Q8wPCA
          oPNHlBNg/YAErDuKsfeoBudpRakbHuucDEL9BLwOAoC1bBBQgOP6/j1A+5hVZ9bl
          d1YXxkDR6odHEndfMTYHAtdiuYY6D2F3c6tESgnuksuAIuHRLnptIKrbC4HzBZG7
          A8glSdSPBaCjMV8jnl2ge0XnIWbKYWXrWBaLIQ==
          -----END CERTIFICATE-----
    ...
    """)

_ENCRYPTED_SECRET = textwrap.dedent(
    """
    ---
    schema: pegleg/PeglegManagedDocument/v1
    metadata:
      name: encrypted-secret
      schema: metadata/Document/v1
      labels: {}
      layeringDefinition:
        abstract: false
        layer: site
      storagePolicy: cleartext
    data:
      managedDocument:
        schema: deckhand/Passphrase/v1
        metadata:
          layeringDefinition:
            abstract: false
            layer: site
          storagePolicy: encrypted
          name: encrypted-secret
          schema: metadata/Document/v1
        data: !!binary |
          Z0FBQUFBQmVxeHkwQ2JCYy1lMmFIU0ZCcGJTdUp4OFlyM2t4TmYwRXJndTRVTFE5SFozYVd0eFVJ
          SkhPRTdCRGppb3NhVjFQRkN0WXhaSmZWdjRHZkZTUzFBU0xGSS1vdWVVYUUxaEVfN1d5RmdUNkFw
          RXM2NjA9
      encrypted:
        by: alexanderhughes
        at: '2020-04-30T18:45:08.794873'
    ...
    """)


@pytest.fixture()
def create_tmp_site_structure(tmpdir):
    """Fixture that creates a temporary site directory structure

    :returns: Function pointer, which, when called, creates a temporary file
        structure.

    """
    def _create_tmp_folder_system(sitename):
        """Creates a temporary site folder system.

        :param str sitename: Name of the site.
        """
        # Create site directories and files.
        p = tmpdir.mkdir("deployment_files")
        config.set_site_repo(p.strpath)

        site_definition = copy.deepcopy(_SITE_DEFINITION)
        site_definition = site_definition % {'sitename': sitename}

        test_structure = copy.deepcopy(_SITE_TEST_STRUCTURE)
        test_structure['files']['site-definition.yaml'] = yaml.safe_load(
            site_definition)
        test_structure['files']['layering-definition.yaml'] = yaml.safe_load(
            _LAYERING_DEFINITION)
        test_structure['directories']['secrets']['directories']['passphrases'][
            'files']['plaintext.yaml'] = yaml.safe_load(_PLAINTEXT_SECRET)
        test_structure['directories']['secrets']['directories']['passphrases'][
            'files']['managed.yaml'] = yaml.safe_load(_MANAGED_SECRET)
        test_structure['directories']['secrets']['directories']['passphrases'][
            'files']['encrypted.yaml'] = yaml.safe_load(_ENCRYPTED_SECRET)

        test_path = os.path.join(p.strpath, files._site_path(sitename))
        files._create_tree(test_path, tree=test_structure)

        return p.strpath

    try:
        yield _create_tmp_folder_system
    finally:
        temp_path = config.get_site_repo()
        if temp_path != './' and os.path.exists(temp_path):
            shutil.rmtree(temp_path, ignore_errors=True)


def test_site_render(create_tmp_site_structure):
    sitename = "test"
    rootpath = create_tmp_site_structure(sitename)
    docs = site.get_rendered_docs(sitename)

    assert len(
        docs) == 5  # Site-definition, layering definition, 3 secrets documents
    for doc in docs:
        if doc['metadata']['name'] == 'plaintext-secret':
            doc2 = yaml.safe_load(_PLAINTEXT_SECRET)
            assert doc2 == doc
        elif doc['metadata']['name'] == 'managed-secret':
            doc2 = yaml.safe_load(_MANAGED_SECRET)
            assert doc2['data']['managedDocument'] == doc
        elif doc['metadata']['name'] == 'encrypted-secret':
            doc2 = yaml.safe_load(_ENCRYPTED_SECRET)
            doc2['data']['managedDocument']['data'] = doc2['data'][
                'managedDocument']['data'].decode()
            assert doc2['data']['managedDocument'] == doc

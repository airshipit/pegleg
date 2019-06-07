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
import os

import mock
import pytest
import yaml

from pegleg import config
from pegleg.engine import bundle
from pegleg.engine.exceptions import GenesisBundleEncryptionException
from pegleg.engine.exceptions import GenesisBundleGenerateException
from pegleg.engine.util import files

from tests.unit.fixtures import temp_path

SITE_DEFINITION = """
---
# High-level pegleg site definition file
schema: pegleg/SiteDefinition/v1
metadata:
  schema: metadata/Document/v1
  layeringDefinition:
    abstract: false
    layer: site
  # NEWSITE-CHANGEME: Replace with the site name
  name: test_site
  storagePolicy: cleartext
data:
  # The type layer this site will delpoy with. Type layer is found in the
  # type folder.
  site_type: foundry
...

"""

SITE_CONFIG_DATA = """
---
schema: promenade/EncryptionPolicy/v1
metadata:
  schema: metadata/Document/v1
  name: encryption-policy
  layeringDefinition:
    abstract: false
    layer: site
  storagePolicy: cleartext
data:
  scripts:
    genesis:
      gpg: {}
    join:
      gpg: {}
---
schema: deckhand/LayeringPolicy/v1
metadata:
  schema: metadata/Control/v1
  name: layering-policy
data:
  layerOrder:
    - global
    - type
    - site
---
schema: deckhand/Passphrase/v1
metadata:
  schema: metadata/Document/v1
  name: ceph_swift_keystone_password
  layeringDefinition:
    abstract: false
    layer: site
  storagePolicy: cleartext
data: ABAgagajajkb839215387
...
"""


@mock.patch.dict(os.environ, {
    'PEGLEG_PASSPHRASE': 'ytrr89erARAiPE34692iwUMvWqqBvC',
    'PEGLEG_SALT': 'MySecretSalt1234567890]['
})
def test_no_encryption_key(temp_path):
    # Write the test data to temp file
    config_data = list(yaml.safe_load_all(SITE_CONFIG_DATA))
    base_config_dir = os.path.join(temp_path, 'config_dir')
    config.set_site_repo(base_config_dir)
    config_dir = os.path.join(base_config_dir, 'site', 'test_site')

    config_path = os.path.join(config_dir, 'config_file.yaml')
    build_dir = os.path.join(temp_path, 'build_dir')
    os.makedirs(config_dir)

    files.write(config_path, config_data)
    files.write(os.path.join(config_dir, "site-definition.yaml"),
                yaml.safe_load_all(SITE_DEFINITION))

    with pytest.raises(GenesisBundleEncryptionException,
                       match=r'.*no encryption policy or key is specified.*'):
        bundle.build_genesis(build_path=build_dir,
                             encryption_key=None,
                             validators=False,
                             debug=logging.ERROR,
                             site_name="test_site")


@mock.patch.dict(os.environ, {
    'PEGLEG_PASSPHRASE': 'ytrr89erARAiPE34692iwUMvWqqBvC',
    'PEGLEG_SALT': 'MySecretSalt1234567890]['
})
def test_failed_deckhand_validation(temp_path):
    # Write the test data to temp file
    config_data = list(yaml.safe_load_all(SITE_CONFIG_DATA))
    base_config_dir = os.path.join(temp_path, 'config_dir')
    config.set_site_repo(base_config_dir)
    config_dir = os.path.join(base_config_dir, 'site', 'test_site')

    config_path = os.path.join(config_dir, 'config_file.yaml')
    build_dir = os.path.join(temp_path, 'build_dir')
    os.makedirs(config_dir)
    files.write(config_path, config_data)
    files.write(os.path.join(config_dir, "site-definition.yaml"),
                yaml.safe_load_all(SITE_DEFINITION))
    key = 'MyverYSecretEncryptionKey382803'
    with pytest.raises(GenesisBundleGenerateException,
                       match=r'.*failed on deckhand validation.*'):
        bundle.build_genesis(build_path=build_dir,
                             encryption_key=key,
                             validators=False,
                             debug=logging.ERROR,
                             site_name="test_site")

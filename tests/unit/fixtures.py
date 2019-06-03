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

from __future__ import absolute_import
import copy
import os
import shutil
import tempfile

import pytest
import yaml

from pegleg import config
from pegleg.engine.util import files

TEST_DOCUMENT = """
---
schema: deckhand/Passphrase/v1
metadata:
  schema: metadata/Document/v1
  name: %(name)s
  storagePolicy: %(storagePolicy)s
  layeringDefinition:
    abstract: False
    layer: %(layer)s
data: %(name)s-password
...
"""


def _gen_document(**kwargs):
    if "storagePolicy" not in kwargs:
        kwargs["storagePolicy"] = "cleartext"
    test_document = TEST_DOCUMENT % kwargs
    return yaml.safe_load(test_document)


@pytest.fixture()
def create_tmp_deployment_files(tmpdir):
    """Fixture that creates a temporary directory structure."""
    sitenames = ['cicd', 'lab']

    SITE_TEST_STRUCTURE = {
        'directories': {
            'secrets': {
                'directories': {
                    'passphrases': {
                        'files': {}
                    },
                },
            },
            'software': {
                'directories': {
                    'charts': {
                        'files': {}
                    },
                },
            },
        },
        'files': {}
    }

    p = tmpdir.mkdir("deployment_files")
    config.set_site_repo(str(p))

    # Create global directories and files.
    files._create_tree(
        os.path.join(str(p), 'global'),
        tree={
            'directories': {
                'common': {
                    'files': {
                        'global-common.yaml':
                        _gen_document(name="global-common", layer='global')
                    }
                },
                'v1.0': {
                    'files': {
                        'global-v1.0.yaml':
                        _gen_document(name="global-v1.0", layer='global')
                    }
                }
            }
        })

    # Create type directories and files.
    files._create_tree(
        os.path.join(str(p), 'type'),
        tree={
            'directories': {
                site: {
                    'directories': {
                        'common': {
                            'files': {
                                '%s-type-common.yaml' % site:
                                _gen_document(
                                    name="%s-type-common" % site, layer='type')
                            }
                        },
                        'v1.0': {
                            'files': {
                                '%s-type-v1.0.yaml' % site:
                                _gen_document(
                                    name="%s-type-v1.0" % site, layer='type')
                            }
                        }
                    }
                }
                for site in sitenames
            }
        })

    # Create site directories and files.
    for site in sitenames:
        site_definition = """
---
data:
  repositories:
    global:
      revision: v1.0
      url: http://nothing.com
  site_type: %s
metadata:
  layeringDefinition: {abstract: false, layer: site}
  name: %s
  schema: metadata/Document/v1
  storagePolicy: cleartext
schema: pegleg/SiteDefinition/v1
""" % (site, site)

        test_structure = SITE_TEST_STRUCTURE.copy()
        test_structure['directories']['secrets']['directories']['passphrases'][
            'files'] = {
                '%s-passphrase.yaml' % site:
                _gen_document(name="%s-passphrase" % site, layer='site')
            }
        test_structure['directories']['software']['directories']['charts'][
            'files'] = {
                '%s-chart.yaml' % site:
                _gen_document(name="%s-chart" % site, layer='site')
            }
        test_structure['files']['site-definition.yaml'] = yaml.safe_load(
            site_definition)

        cicd_path = os.path.join(str(p), files._site_path(site))
        files._create_tree(cicd_path, tree=test_structure)

    yield tmpdir


@pytest.fixture()
def temp_path():
    temp_folder = tempfile.mkdtemp()
    try:
        yield temp_folder
    finally:
        if os.path.exists(temp_folder):
            shutil.rmtree(temp_folder, ignore_errors=True)

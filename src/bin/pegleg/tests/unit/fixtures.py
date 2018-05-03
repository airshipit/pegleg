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
import os
import tempfile

import pytest
import yaml

from pegleg import config
from pegleg.engine.util import files


@pytest.fixture()
def create_tmp_deployment_files(tmpdir):
    """Fixture that creates a temporary directory structure."""
    orig_primary_repo = config.get_primary_repo()
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
    config.set_primary_repo(str(p))

    # Create global directories and files.
    files._create_tree(
        os.path.join(str(p), 'global'),
        tree={
            'directories': {
                'common': {
                    'files': {
                        'global-common.yaml': 'global-common'
                    }
                },
                'v1.0': {
                    'files': {
                        'global-v1.0.yaml': 'global-v1.0'
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
                                ('%s-type-common' % site)
                            }
                        },
                        'v1.0': {
                            'files': {
                                '%s-type-v1.0.yaml' % site:
                                ('%s-type-v1.0' % site)
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
  revision: v1.0
  site_type: %s
metadata:
  layeringDefinition: {abstract: false, layer: site}
  name: %s
  schema: metadata/Document/v1
  storagePolicy: cleartext
schema: pegleg/SiteDefinition/v1
...
""" % (site, site)

        test_structure = SITE_TEST_STRUCTURE.copy()
        test_structure['directories']['secrets']['directories']['passphrases'][
            'files'] = {
                '%s-passphrase.yaml' % site: '%s-passphrase' % site
            }
        test_structure['directories']['software']['directories']['charts'][
            'files'] = {
                '%s-chart.yaml' % site: '%s-chart' % site
            }
        test_structure['files']['site-definition.yaml'] = yaml.safe_load(
            site_definition)

        cicd_path = os.path.join(str(p), files._site_path(site))
        files._create_tree(cicd_path, tree=test_structure)

    yield

    config.set_primary_repo(orig_primary_repo)

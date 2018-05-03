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

import tempfile

from pegleg import config
from pegleg.engine.util import files
from tests.unit.fixtures import create_tmp_deployment_files


def test_no_non_yamls(tmpdir):
    p = tmpdir.mkdir("deployment_files").mkdir("global")
    for x in range(3):  # Create 3 YAML files
        p.join("good-%d.yaml" % x).write('fake-content')
    p.join("bad.txt").write("fake-content")
    config.set_primary_repo(str(tmpdir.listdir()[0]))
    results = list(files.all())

    assert 3 == len(results)
    # Make sure only YAML files are returned
    for i in results:
        assert i.endswith('.yaml')


def test_list_all_files(create_tmp_deployment_files):
    expected_files = sorted([
        'deployment_files/global/common/global-common.yaml',
        'deployment_files/global/v1.0/global-v1.0.yaml',
        'deployment_files/type/cicd/common/cicd-type-common.yaml',
        'deployment_files/type/cicd/v1.0/cicd-type-v1.0.yaml',
        'deployment_files/type/lab/common/lab-type-common.yaml',
        'deployment_files/type/lab/v1.0/lab-type-v1.0.yaml',
        'deployment_files/site/cicd/secrets/passphrases/cicd-passphrase.yaml',
        'deployment_files/site/cicd/site-definition.yaml',
        'deployment_files/site/cicd/software/charts/cicd-chart.yaml',
        'deployment_files/site/lab/secrets/passphrases/lab-passphrase.yaml',
        'deployment_files/site/lab/site-definition.yaml',
        'deployment_files/site/lab/software/charts/lab-chart.yaml',
    ])
    actual_files = sorted(files.all())

    assert len(actual_files) == len(expected_files)
    for idx, file in enumerate(actual_files):
        assert file.endswith(expected_files[idx])

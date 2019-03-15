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

import pytest
import yaml

from pegleg import config
from pegleg.engine.util import files
from tests.unit.fixtures import create_tmp_deployment_files
from tests.unit.fixtures import temp_path


class TestFileHelpers(object):
    def test_read_compatible_file(self, create_tmp_deployment_files):
        path = os.path.join(config.get_site_repo(), 'site', 'cicd', 'secrets',
                            'passphrases', 'cicd-passphrase.yaml')
        documents = files.read(path)
        assert 1 == len(documents)

    def test_read_incompatible_file(self, create_tmp_deployment_files):
        # NOTE(felipemonteiro): The Pegleg site-definition.yaml is a
        # Deckhand-formatted document currently but probably shouldn't be,
        # because it has no business being in Deckhand. As such, validate that
        # it is ignored.
        path = os.path.join(config.get_site_repo(), 'site', 'cicd',
                            'site-definition.yaml')
        documents = files.read(path)
        assert not documents, ("Documents returned should be empty for "
                               "site-definition.yaml")

    def test_write(self, create_tmp_deployment_files):
        path = os.path.join(config.get_site_repo(), 'site', 'cicd',
                            'test_out.yaml')
        files.write(path, "test text")
        with open(path, "r") as out_fi:
            assert out_fi.read() == "test text"

        files.write(path, {"a": 1})
        with open(path, "r") as out_fi:
            assert yaml.safe_load(out_fi) == {"a": 1}

        files.write(path, [{"a": 1}])
        with open(path, "r") as out_fi:
            assert list(yaml.safe_load_all(out_fi)) == [{"a": 1}]

        with pytest.raises(ValueError) as _:
            files.write(path, object())


def test_file_in_subdir():
    assert files.file_in_subdir("aaa/bbb/ccc.txt", "aaa")
    assert files.file_in_subdir("aaa/bbb/ccc.txt", "bbb")
    assert not files.file_in_subdir("aaa/bbb/ccc.txt", "ccc")
    assert not files.file_in_subdir("aaa/bbb/ccc.txt", "bb")
    assert not files.file_in_subdir("aaa/bbb/../ccc.txt", "bbb")


def test_read(temp_path):
    # This will throw an error if yaml attempts to read the tag.
    with open(os.path.join(temp_path, "invalid.yaml"), "w") as invalid_yaml:
        invalid_yaml.write("!!python/name:fake_class''\n")
        files.read(os.path.join(temp_path, "invalid.yaml"))

    # Under PyYAML's default behavior, the tag !!python/name:builtins.int
    # will be parsed into the method int. files.read should ignore this tag.
    with open(os.path.join(temp_path, "valid.yaml"), "w") as valid_yaml:
        valid_yaml.write("!!python/name:builtins.int ''\n")
    read_files = files.read(os.path.join(temp_path, "valid.yaml"))
    # Assert that the tag was not parsed into the method int
    assert int not in read_files

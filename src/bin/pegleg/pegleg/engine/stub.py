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

from pegleg.engine import util

__all__ = ['global_', 'site', 'site_type']


def global_(revision):
    util.files.create_global_directories(revision)


def site(revision, site_type, site_name):
    util.definition.create(
        revision=revision, site_name=site_name, site_type=site_type)
    params = util.definition.load_as_params(site_name)
    util.files.create_site_directories(**params)


def site_type(revision, site_type):
    util.files.create_site_type_directories(
        revision=revision, site_type=site_type)

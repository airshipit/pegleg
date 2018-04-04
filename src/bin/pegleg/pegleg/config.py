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

try:
    if GLOBAL_CONTEXT:
        pass
except NameError:
    GLOBAL_CONTEXT = {
        'primary_repo': './',
        'aux_repos': [],
    }


def get_primary_repo():
    return GLOBAL_CONTEXT['primary_repo']


def set_primary_repo(r):
    GLOBAL_CONTEXT['primary_repo'] = r.rstrip('/') + '/'


def set_auxiliary_repo_list(a):
    GLOBAL_CONTEXT['aux_repos'] = [r.rstrip('/') + '/' for r in a]


def add_auxiliary_repo(a):
    GLOBAL_CONTEXT['aux_repos'].append(a.rstrip('/') + '/')


def get_auxiliary_repo_list():
    return GLOBAL_CONTEXT['aux_repos']


def each_auxiliary_repo():
    for a in GLOBAL_CONTEXT['aux_repos']:
        yield a


def all_repos():
    repos = [get_primary_repo()]
    repos.extend(get_auxiliary_repo_list())
    return repos

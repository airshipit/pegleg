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
        'site_repo': './',
        'extra_repos': [],
        'site_path': 'site'
    }


def get_site_repo():
    return GLOBAL_CONTEXT['site_repo']


def set_site_repo(r):
    GLOBAL_CONTEXT['site_repo'] = r.rstrip('/') + '/'


def get_extra_repo_store():
    return GLOBAL_CONTEXT.get('extra_repo_store', [])


def set_extra_repo_store(r):
    GLOBAL_CONTEXT['extra_repo_store'] = r


def set_repo_key(k):
    GLOBAL_CONTEXT['repo_key'] = k


def get_repo_key():
    return GLOBAL_CONTEXT.get('repo_key', None)


def set_repo_username(u):
    GLOBAL_CONTEXT['repo_username'] = u


def get_repo_username():
    return GLOBAL_CONTEXT.get('repo_username', None)


def set_extra_repo_list(a):
    GLOBAL_CONTEXT['extra_repos'] = [r.rstrip('/') + '/' for r in a]


def add_extra_repo(a):
    GLOBAL_CONTEXT['extra_repos'].append(a.rstrip('/') + '/')


def get_extra_repo_list():
    return GLOBAL_CONTEXT['extra_repos']


def each_extra_repo():
    for a in GLOBAL_CONTEXT['extra_repos']:
        yield a


def all_repos():
    repos = [get_site_repo()]
    repos.extend(get_extra_repo_list())
    return repos


def get_rel_site_path():
    return GLOBAL_CONTEXT.get('site_path', 'site')


def set_rel_site_path(p):
    p = p or 'site'
    GLOBAL_CONTEXT['site_path'] = p

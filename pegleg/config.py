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

# TODO(felipemonteiro): This pattern below should be swapped out for click
# context passing but will require a somewhat heavy code refactor. See:
# http://click.pocoo.org/5/commands/#nested-handling-and-contexts

try:
    if GLOBAL_CONTEXT:
        pass
except NameError:
    GLOBAL_CONTEXT = {
        'site_repo': './',
        'extra_repos': [],
        'clone_path': None,
        'site_path': 'site',
        'type_path': 'type'
    }


def get_site_repo():
    """Get the primary site repository specified via ``-r`` CLI flag."""
    return GLOBAL_CONTEXT['site_repo']


def set_site_repo(r):
    """Set the primary site repository."""
    GLOBAL_CONTEXT['site_repo'] = r.rstrip('/') + '/'


def get_clone_path():
    """Get specified clone path (corresponds to ``-p`` CLI flag)."""
    return GLOBAL_CONTEXT['clone_path']


def set_clone_path(p):
    """Set specified clone path (corresponds to ``-p`` CLI flag)."""
    GLOBAL_CONTEXT['clone_path'] = p


def get_extra_repo_overrides():
    """Get extra repository overrides specified via ``-e`` CLI flag."""
    return GLOBAL_CONTEXT.get('extra_repo_overrides', [])


def set_extra_repo_overrides(r):
    """Set extra repository overrides.

    .. note:: Only CLI should call this.
    """
    GLOBAL_CONTEXT['extra_repo_overrides'] = r


def set_repo_key(k):
    """Set additional repository key, like extra metadata to track."""
    GLOBAL_CONTEXT['repo_key'] = k


def get_repo_key():
    """Get additional repository key."""
    return GLOBAL_CONTEXT.get('repo_key', None)


def set_repo_username(u):
    """Set repo username for SSH auth, corresponds to ``-u`` CLI flag."""
    GLOBAL_CONTEXT['repo_username'] = u


def get_repo_username():
    """Get repo username for SSH auth."""
    return GLOBAL_CONTEXT.get('repo_username', None)


def set_extra_repo_list(a):
    """Set the extra repository list to be used by ``pegleg.engine``."""
    GLOBAL_CONTEXT['extra_repos'] = [r.rstrip('/') + '/' for r in a]


def get_extra_repo_list():
    """Get the extra repository list.

    .. note::

        Use this instead of ``get_extra_repo_overrides`` as it handles
        both overrides and site-definition.yaml defaults.
    """
    return GLOBAL_CONTEXT['extra_repos']


def add_extra_repo(a):
    """Add an extra repo to the extra repository list."""
    GLOBAL_CONTEXT['extra_repos'].append(a.rstrip('/') + '/')


def each_extra_repo():
    """Iterate over each extra repo."""
    for a in GLOBAL_CONTEXT['extra_repos']:
        yield a


def all_repos():
    """Return the primary site repo, in addition to all extra ones."""
    repos = [get_site_repo()]
    repos.extend(get_extra_repo_list())
    return repos


def get_rel_site_path():
    """Get the relative site path name, default is "site"."""
    return GLOBAL_CONTEXT.get('site_path', 'site')


def set_rel_site_path(p):
    """Set the relative site path name."""
    p = p or 'site'
    GLOBAL_CONTEXT['site_path'] = p


def get_rel_type_path():
    """Get the relative type path name, default is "type"."""
    return GLOBAL_CONTEXT.get('type_path', 'type')


def set_rel_type_path(p):
    """Set the relative type path name."""
    p = p or 'type'
    GLOBAL_CONTEXT['type_path'] = p

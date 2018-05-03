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

import click
import os
import yaml
import logging

from pegleg import config

LOG = logging.getLogger(__name__)

__all__ = [
    'all',
    'create_global_directories',
    'create_site_directories',
    'create_site_type_directories',
    'directories_for',
    'directory_for',
    'dump',
    'existing_directories',
    'search',
    'slurp',
]

DIR_DEPTHS = {
    'global': 1,
    'type': 2,
    'site': 1,
}


def all():
    return search([
        os.path.join(r, k) for r in config.all_repos()
        for k in DIR_DEPTHS.keys()
    ])


def create_global_directories(revision):
    _create_tree(_global_common_path())
    _create_tree(_global_revision_path(revision))


def create_site_directories(*, site_name, revision, **_kwargs):
    _create_tree(_site_path(site_name))


def create_site_type_directories(*, revision, site_type):
    _create_tree(_site_type_common_path(site_type))
    _create_tree(_site_type_revision_path(site_type, revision))


FULL_STRUCTURE = {
    'directories': {
        'baremetal': {},
        'deployment': {},
        'networks': {
            'directories': {
                'physical': {},
            },
        },
        'pki': {},
        'profiles': {
            'directories': {
                'hardware': {},
                'host': {},
            }
        },
        'schemas': {},
        'secrets': {
            'directories': {
                'certificate-authorities': {},
                'certificates': {},
                'keypairs': {},
                'passphrases': {},
            },
        },
        'software': {
            'directories': {
                'charts': {},
                'config': {},
                'manifests': {},
            },
        },
    },
}


def _create_tree(root_path, *, tree=FULL_STRUCTURE):
    for name, data in tree.get('directories', {}).items():
        path = os.path.join(root_path, name)
        os.makedirs(path, mode=0o775, exist_ok=True)
        _create_tree(path, tree=data)

    for filename, yaml_data in tree.get('files', {}).items():
        path = os.path.join(root_path, filename)
        with open(path, 'w') as f:
            yaml.safe_dump(yaml_data, f)


def directories_for(*, site_name, revision, site_type):
    library_list = [
        _global_common_path(),
        _global_revision_path(revision),
        _site_type_common_path(site_type),
        _site_type_revision_path(site_type, revision),
        _site_path(site_name),
    ]

    return [
        os.path.join(b, l) for b in config.all_repos() for l in library_list
    ]


def directories_for_each_repo(*, site_name, revision, site_type):
    """Provide directories for each repo.

    When producing bucketized output files, the documents collected
    must be collated by repo. Provide the list of source directories
    by repo.
    """
    library_list = [
        _global_common_path(),
        _global_revision_path(revision),
        _site_type_common_path(site_type),
        _site_type_revision_path(site_type, revision),
        _site_path(site_name),
    ]

    dir_map = dict()
    for r in config.all_repos():
        dir_map[r] = [os.path.join(r, l) for l in library_list]

    return dir_map


def _global_common_path():
    return 'global/common'


def _global_revision_path(revision):
    return 'global/%s' % revision


def _site_type_common_path(site_type):
    return 'type/%s/common' % site_type


def _site_type_revision_path(site_type, revision):
    return 'type/%s/%s' % (site_type, revision)


def _site_path(site_name):
    return 'site/%s' % site_name


def list_sites(primary_repo_base=None):
    """Get a list of site definition directories in the primary repo."""
    if not primary_repo_base:
        primary_repo_base = config.get_primary_repo()
    for path in os.listdir(os.path.join(primary_repo_base, 'site')):
        joined_path = os.path.join(primary_repo_base, 'site', path)
        if os.path.isdir(joined_path):
            yield path


def directory_for(*, path):
    for r in config.all_repos():
        if path.startswith(r):
            partial_path = path[len(r):]
            parts = os.path.normpath(partial_path).split(os.sep)
            depth = DIR_DEPTHS.get(parts[0])
            if depth is not None:
                return os.path.join(r, *parts[:depth + 1])


def existing_directories():
    directories = set()
    for r in config.all_repos():
        for search_path, depth in DIR_DEPTHS.items():
            directories.update(
                _recurse_subdirs(os.path.join(r, search_path), depth))
    return directories


def slurp(path):
    if not os.path.exists(path):
        raise click.ClickException(
            '%s not found.  pegleg must be run from '
            'the root of a configuration repostiory.' % path)

    with open(path) as f:
        try:
            return yaml.safe_load(f)
        except Exception as e:
            raise click.ClickException('Failed to parse %s:\n%s' % (path, e))


def dump(path, data):
    if os.path.exists(path):
        raise click.ClickException('%s already exists, aborting' % path)

    os.makedirs(os.path.dirname(path), mode=0o775, exist_ok=True)

    with open(path, 'w') as f:
        yaml.dump(data, f, explicit_start=True)


def _recurse_subdirs(search_path, depth):
    directories = set()
    try:
        for path in os.listdir(search_path):
            joined_path = os.path.join(search_path, path)
            if os.path.isdir(joined_path):
                if depth == 1:
                    directories.add(joined_path)
                else:
                    directories.update(
                        _recurse_subdirs(joined_path, depth - 1))
    except FileNotFoundError:
        pass
    return directories


def search(search_paths):
    for search_path in search_paths:
        LOG.debug("Recursively collecting YAMLs from %s" % search_path)
        for root, _dirs, filenames in os.walk(search_path):
            for filename in filenames:
                if filename.endswith(".yaml"):
                    yield os.path.join(root, filename)

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

import collections
import logging
import os

import click
import yaml
from yaml.constructor import SafeConstructor

from pegleg import config
from pegleg.engine import util
from pegleg.engine.util import pegleg_managed_document as md

LOG = logging.getLogger(__name__)

__all__ = [
    'all',
    'create_global_directories',
    'create_site_directories',
    'create_site_type_directories',
    'directories_for',
    'directory_for',
    'dump',
    'safe_dump',
    'dump_all',
    'read',
    'write',
    'existing_directories',
    'search',
    'slurp',
    'check_file_save_location',
    'collect_files_by_repo',
]

DIR_DEPTHS = {
    'global': 1,
    'type': 2,
    'site': 1,
}


def all():
    return search(
        [
            os.path.join(r, k) for r in config.all_repos()
            for k in DIR_DEPTHS.keys()
        ])


def create_global_directories():
    # NOTE(felipemonteiro): Currently unused. Needed by old "stub" CLI command.
    # Keeping this around because this utility may have future value.
    _create_tree(_global_root_path())
    _create_tree(_global_common_path())


def create_site_directories(*, site_name, **_kwargs):
    # NOTE(felipemonteiro): Currently unused. Needed by old "stub" CLI command.
    # Keeping this around because this utility may have future value.
    _create_tree(_site_path(site_name))


def create_site_type_directories(*, site_type):
    # NOTE(felipemonteiro): Currently unused. Needed by old "stub" CLI command.
    # Keeping this around because this utility may have future value.
    _create_tree(_site_type_common_path(site_type))
    _create_tree(_site_type_root_path(site_type))


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
        os.makedirs(os.path.abspath(path), exist_ok=True)
        _create_tree(path, tree=data)

    for filename, yaml_data in tree.get('files', {}).items():
        path = os.path.join(root_path, filename)
        with open(path, 'w') as f:
            yaml.safe_dump(yaml_data, f)


def directories_for(*, site_name, site_type):
    library_list = [
        _global_root_path(),
        _site_type_root_path(site_type),
        _site_path(site_name),
    ]

    return [
        os.path.join(b, l) for b in config.all_repos() for l in library_list
    ]


def directories_for_each_repo(*, site_name, site_type):
    """Provide directories for each repo.

    When producing bucketized output files, the documents collected
    must be collated by repo. Provide the list of source directories
    by repo.
    """
    library_list = [
        _global_root_path(),
        _site_type_root_path(site_type),
        _site_path(site_name),
    ]

    dir_map = dict()
    for r in config.all_repos():
        dir_map[r] = [os.path.join(r, l) for l in library_list]

    return dir_map


def _global_common_path():
    return 'global/common'


def _global_root_path():
    return 'global'


def _site_type_common_path(site_type):
    return 'type/%s/common' % site_type


def _site_type_root_path(site_type):
    return 'type/%s' % site_type


def _site_path(site_name):
    return os.path.join(config.get_rel_site_path(), site_name)


def list_sites(primary_repo_base=None):
    """Get a list of site definition directories in the primary repo."""
    if not primary_repo_base:
        primary_repo_base = config.get_site_repo()
    full_site_path = os.path.join(
        primary_repo_base, config.get_rel_site_path())
    for path in os.listdir(full_site_path):
        joined_path = os.path.join(full_site_path, path)
        if os.path.isdir(joined_path):
            yield path


def list_types(primary_repo_base=None):
    """Get a list of type directories in the primary repo."""
    if not primary_repo_base:
        primary_repo_base = config.get_site_repo()
    full_type_path = os.path.join(
        primary_repo_base, config.get_rel_type_path())
    for path in os.listdir(full_type_path):
        joined_path = os.path.join(full_type_path, path)
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
            '%s not found. Pegleg must be run from the root of a configuration'
            ' repository.' % path)

    with open(path, 'r') as f:
        try:
            # Ignore YAML tags, only construct dicts
            SafeConstructor.add_multi_constructor(
                '', lambda loader, suffix, node: None)
            return yaml.safe_load(f)
        except Exception as e:
            raise click.ClickException('Failed to parse %s:\n%s' % (path, e))


def dump(data, path, flag='w', **kwargs):
    add_representer_ordered_dict()
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, flag) as f:

        yaml.dump(data, f, **kwargs)


def safe_dump(data, path, flag='w', **kwargs):
    add_representer_ordered_dict()
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, flag) as f:

        yaml.safe_dump(data, f, **kwargs)


def dump_all(data, path, flag='w', **kwargs):
    add_representer_ordered_dict()
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    with open(path, flag) as f:

        yaml.dump_all(data, f, **kwargs)


def read(path):
    """
    Read the yaml file ``path`` and return its contents as a list of
    dicts
    """

    if not os.path.exists(path):
        raise click.ClickException(
            '{} not found. Pegleg must be run from the root of a '
            'configuration repository.'.format(path))

    def is_deckhand_document(document):
        # Deckhand documents only consist of control and application
        # documents.
        valid_schemas = ('metadata/Control', 'metadata/Document')
        if isinstance(document, dict):
            schema = document.get('metadata', {}).get('schema', '')
            # NOTE(felipemonteiro): The Pegleg site-definition.yaml is a
            # Deckhand-formatted document currently but probably shouldn't
            # be, because it has no business being in Deckhand. As such,
            # treat it as a special case.
            if "SiteDefinition" in document.get('schema', ''):
                return False
            if any(schema.startswith(x) for x in valid_schemas):
                return True
            else:
                LOG.debug(
                    'Document with schema=%s is not a valid Deckhand '
                    'schema. Ignoring it.', schema)
        return False

    def is_pegleg_managed_document(document):
        return md.PeglegManagedSecretsDocument.is_pegleg_managed_secret(
            document)

    with open(path, 'r') as stream:
        # Ignore YAML tags, only construct dicts
        SafeConstructor.add_multi_constructor(
            '', lambda loader, suffix, node: None)
        try:
            return [
                d for d in yaml.safe_load_all(stream) if d and (
                    is_deckhand_document(d) or is_pegleg_managed_document(d))
            ]
        except yaml.YAMLError as e:
            raise click.ClickException('Failed to parse %s:\n%s' % (path, e))


def write(data, file_path, sort_keys=False):
    """
    Write the data to destination file_path.

    If the directory structure of the file_path should not exist, create it.
    If the file should exit, overwrite it with new data,

    :param file_path: Destination file for the written data file
    :type file_path: str
    :param data: data to be written to the destination file
    :type data: str, dict, or a list of dicts
    :param sort_keys: sort keys alphabetically in output yaml
    :type sort_keys: bool
    """
    add_representer_ordered_dict()
    try:
        os.makedirs(os.path.dirname(os.path.abspath(file_path)), exist_ok=True)
        with open(file_path, 'w') as stream:
            if isinstance(data, str):
                stream.write(data)
            elif isinstance(data, (dict, collections.abc.Iterable)):
                if isinstance(data, dict):
                    data = [data]
                yaml.safe_dump_all(
                    data,
                    stream,
                    sort_keys=sort_keys,
                    explicit_start=True,
                    explicit_end=True,
                    default_flow_style=False)
            else:
                raise ValueError(
                    'data must be str or dict, '
                    'not {}'.format(type(data)))
    except EnvironmentError as e:
        raise click.ClickError(
            "Couldn't write data to {}: {}".format(file_path, e))


def add_representer_ordered_dict():
    yaml.add_representer(
        collections.OrderedDict,
        lambda dumper, dict_data: dumper.represent_mapping(
            'tag:yaml.org,2002:map', dict_data.items()))
    yaml.add_representer(
        collections.OrderedDict,
        lambda dumper, dict_data: dumper.represent_mapping(
            'tag:yaml.org,2002:map', dict_data.items()), yaml.SafeDumper)


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
    if not isinstance(search_paths, (list, tuple)):
        search_paths = [search_paths]

    for search_path in search_paths:
        LOG.debug("Recursively collecting YAMLs from %s", search_path)
        for root, _, filenames in os.walk(search_path):

            # Ignore hidden folders like .tox or .git for faster processing.
            if os.path.basename(root).startswith("."):
                continue
            # Skip over anything in tools/ because it will never contain valid
            # Pegleg-owned manifest documents.
            if "tools" in root.split("/"):
                continue

            for filename in filenames:
                # Ignore files like .zuul.yaml.
                if filename.startswith("."):
                    continue
                if filename.endswith(".yaml"):
                    yield os.path.join(root, filename)


def check_file_save_location(save_location):
    """
    Verify exists and is a valid directory. If it does not exist create it.

    :param save_location: Base directory to save the result of the
    encryption or decryption of site secrets.
    :type save_location: string, directory path
    :raises click.ClickException: If pre-flight check should fail.
    """

    if save_location:
        if not os.path.exists(save_location):
            LOG.debug(
                "Save location %s does not exist. Creating "
                "automatically.", save_location)
            os.makedirs(os.path.abspath(save_location))
        # In case save_location already exists and isn't a directory.
        if not os.path.isdir(save_location):
            raise click.ClickException(
                'save_location %s already exists, '
                'but is not a directory'.format(save_location))


def collect_files_by_repo(site_name):
    """Collects file by repo name in memory."""

    collected_files_by_repo = collections.defaultdict(list)
    for repo_base, filename in util.definition.site_files_by_repo(site_name):
        repo_name = os.path.normpath(repo_base).split(os.sep)[-1]
        documents = util.files.read(filename)
        collected_files_by_repo[repo_name].extend(documents)
    return collected_files_by_repo


def file_in_subdir(filename, _dir):
    """
    Check if a folder named _dir is in the path to the file

    :return: Whether _dir is a parent of the file
    :rtype: bool
    """
    file_path, filename = os.path.split(os.path.realpath(filename))
    return _dir in file_path.split(os.path.sep)


def path_leaf(path):
    """
    Return the last element in a path, UNLESS it's empty,
    then return the second to last element (unlike os.path.split)

    :param path: a path as a string
    :return: the last non-empty element of a string
    :rtype: str
    """
    split_path = [i for i in path.split(os.sep) if i]
    if split_path:
        return split_path[-1]
    else:
        return None

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
"""Utility functions for site-definition.yaml files."""

import os

import click

from pegleg import config
from pegleg.engine.util import files

__all__ = [
    'load', 'load_as_params', 'path', 'pluck', 'site_files',
    'site_files_by_repo', 'documents_for_each_site', 'documents_for_site'
]


def load(site, primary_repo_base=None):
    return files.slurp(path(site, primary_repo_base))


def load_as_params(site_name, *fields, primary_repo_base=None):
    """Load site definition for given ``site_name`` and return data as params.

    :param str site_name: Name of the site.
    :param iterable fields: List of parameter fields to return. Defaults to
        ``('site_name', 'site_type')``.
    :param str primary_repo_base: Path to primary repository.
    :returns: key-value pairs of parameters, whose keys are a subset of those
        specified by ``fields``.
    :rtype: dict
    """
    if not fields:
        # Default legacy fields.
        fields = ('site_name', 'site_type')

    definition = load(site_name, primary_repo_base)
    params = definition.get('data', {})
    params['site_name'] = site_name
    return {k: v for k, v in params.items() if k in fields}


def path(site_name, primary_repo_base=None):
    """Retrieve path to the site-definition.yaml file for ``site_name``."""
    if not primary_repo_base:
        primary_repo_base = config.get_site_repo()
    return os.path.join(primary_repo_base, 'site', site_name,
                        'site-definition.yaml')


def pluck(site_definition, key):
    try:
        return site_definition['data'][key]
    except Exception as e:
        site_name = site_definition.get('metadata', {}).get('name')
        raise click.ClickException('failed to get "%s" from site definition '
                                   '"%s": %s' % (key, site_name, e))


def site_files(site_name):
    params = load_as_params(site_name)
    for filename in files.search(files.directories_for(**params)):
        yield filename


def site_files_by_repo(site_name):
    """Yield tuples of repo_base, file_name."""
    params = load_as_params(site_name)
    dir_map = files.directories_for_each_repo(**params)
    for repo, dl in dir_map.items():
        for filename in files.search(dl):
            yield (repo, filename)


def documents_for_each_site():
    """Gathers all relevant documents per site, which includes all type and
    global documents that are needed to render each site document.

    :returns: Dictionary of documents, keyed by each site name.
    :rtype: dict

    """

    sitenames = list(files.list_sites())
    documents = {s: [] for s in sitenames}

    for sitename in sitenames:
        params = load_as_params(sitename)
        paths = files.directories_for(**params)
        filenames = set(files.search(paths))
        for filename in filenames:
            documents[sitename].extend(files.read(filename))

    return documents


def documents_for_site(sitename):
    """Gathers all relevant documents for a site, which includes all type and
    global documents that are needed to render each site document.

    :param str sitename: Site name for which to gather documents.
    :returns: List of relevant documents.
    :rtype: list

    """

    documents = []

    params = load_as_params(sitename)
    paths = files.directories_for(**params)
    filenames = set(files.search(paths))
    for filename in filenames:
        documents.extend(files.read(filename))

    return documents

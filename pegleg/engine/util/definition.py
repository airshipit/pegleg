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

import click
import yaml

from pegleg import config
from pegleg.engine.util import files

__all__ = [
    'load', 'load_as_params', 'path', 'pluck', 'site_files',
    'site_files_by_repo', 'documents_for_each_site', 'documents_for_site'
]


def load(site, primary_repo_base=None):
    return files.slurp(path(site, primary_repo_base))


def load_as_params(site_name, primary_repo_base=None):
    definition = load(site_name, primary_repo_base)
    # TODO(felipemonteiro): Currently we are filtering out "revision" from
    # the params that are returned by this function because it is no longer
    # supported. This is a workaround. As soon as the site definition repos
    # switch to real repository format, then we can drop that workaround.
    # Ideally, we should:
    # 1) validate the site-definition.yaml format using lint module
    # 2) extract only the required params here
    params = definition.get('data', {})
    params['site_name'] = site_name
    return params


def path(site_name, primary_repo_base=None):
    if not primary_repo_base:
        primary_repo_base = config.get_site_repo()
    return os.path.join(primary_repo_base, 'site', site_name,
                        'site-definition.yaml')


def pluck(site_definition, key):
    try:
        return site_definition['data'][key]
    except Exception as e:
        site_name = site_definition.get('metadata', {}).get('name')
        raise click.ClickException(
            'failed to get "%s" from site  definition "%s": %s' (key,
                                                                 site_name, e))


def site_files(site_name):
    params = load_as_params(site_name)
    for filename in files.search(
            files.directories_for(
                site_name=params['site_name'], site_type=params['site_type'])):
        yield filename


def site_files_by_repo(site_name):
    """Yield tuples of repo_base, file_name."""
    params = load_as_params(site_name)
    dir_map = files.directories_for_each_repo(
        site_name=params['site_name'], site_type=params['site_type'])
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
        paths = files.directories_for(
            site_name=params['site_name'], site_type=params['site_type'])
        filenames = set(files.search(paths))
        for filename in filenames:
            with open(filename) as f:
                documents[sitename].extend(list(yaml.safe_load_all(f)))

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
    paths = files.directories_for(
        site_name=params['site_name'], site_type=params['site_type'])
    filenames = set(files.search(paths))
    for filename in filenames:
        with open(filename) as f:
            documents.extend(list(yaml.safe_load_all(f)))

    return documents

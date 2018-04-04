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
import collections
import csv
import json
import yaml
import logging

from pegleg.engine import util
__all__ = ['collect', 'impacted', 'list_', 'show', 'render']

LOG = logging.getLogger(__name__)


def collect(site_name, save_location):
    try:
        save_files = dict()
        for (repo_base,
             filename) in util.definition.site_files_by_repo(site_name):
            repo_name = os.path.normpath(repo_base).split(os.sep)[-1]
            if repo_name not in save_files:
                save_files[repo_name] = open(
                    os.path.join(save_location, repo_name + ".yaml"), "w")
            LOG.debug("Collecting file %s to file %s" %
                      (filename,
                       os.path.join(save_location, repo_name + '.yaml')))
            with open(filename) as f:
                save_files[repo_name].writelines(f.readlines())
    except Exception as ex:
        raise click.ClickException("Error saving output: %s" % str(ex))
    finally:
        for f in save_files.values():
            f.close()


def impacted(input_stream, output_stream):
    mapping = _build_impact_mapping()
    impacted_sites = set()

    for line in input_stream:
        line = line.strip()
        directory = util.files.directory_for(path=line)
        if directory is not None:
            impacted_sites.update(mapping[directory])

    for site_name in sorted(impacted_sites):
        output_stream.write(site_name + '\n')


def render(site_name, output_stream):
    documents = []
    for filename in util.definition.site_files(site_name):
        with open(filename) as f:
            documents.extend(list(yaml.safe_load_all(f)))

    rendered_documents, errors = util.deckhand.deckhand_render(
        documents=documents)
    yaml.dump_all(rendered_documents, output_stream, default_flow_style=False)


def list_(output_stream):
    fieldnames = ['site_name', 'site_type', 'revision']
    writer = csv.DictWriter(
        output_stream, fieldnames=fieldnames, delimiter=' ')
    for site_name in util.files.list_sites():
        params = util.definition.load_as_params(site_name)
        writer.writerow(params)


def show(site_name, output_stream):
    data = util.definition.load_as_params(site_name)
    data['files'] = list(util.definition.site_files(site_name))
    json.dump(data, output_stream, indent=2, sort_keys=True)


def _build_impact_mapping():
    mapping = collections.defaultdict(set)

    for site_name in util.files.list_sites():
        params = util.definition.load_as_params(site_name)
        for directory in util.files.directories_for(**params):
            mapping[directory].add(site_name)

    return mapping

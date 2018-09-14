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

import csv
import json
import logging
import os

import click
import yaml

from pegleg.engine import util

__all__ = ('collect', 'list_', 'show', 'render')

LOG = logging.getLogger(__name__)


def _read_and_format_yaml(filename):
    with open(filename) as f:
        lines_to_write = f.readlines()
        if lines_to_write[0] != '---\n':
            lines_to_write = ['---\n'] + lines_to_write
        if lines_to_write[-1] != '...\n':
            lines_to_write.append('...\n')
    return lines_to_write or []


def _collect_to_stdout(site_name):
    """Collects all documents related to ``site_name`` and outputs them to
    stdout via ``output_stream``.
    """
    try:
        for repo_base, filename in util.definition.site_files_by_repo(
                site_name):
            for line in _read_and_format_yaml(filename):
                # This code is a pattern to convert \r\n to \n.
                click.echo("\n".join(line.splitlines()))
    except Exception as ex:
        raise click.ClickException("Error printing output: %s" % str(ex))


def _collect_to_file(site_name, save_location):
    """Collects all documents related to ``site_name`` and outputs them to
    the file denoted by ``save_location``.
    """
    if not os.path.exists(save_location):
        LOG.debug("Collection save location %s does not exist. Creating "
                  "automatically.", save_location)
        os.makedirs(save_location)
    # In case save_location already exists and isn't a directory.
    if not os.path.isdir(save_location):
        raise click.ClickException('save_location %s already exists, but must '
                                   'be a directory' % save_location)

    save_files = dict()
    try:
        for repo_base, filename in util.definition.site_files_by_repo(
                site_name):
            repo_name = os.path.normpath(repo_base).split(os.sep)[-1]
            save_file = os.path.join(save_location, repo_name + '.yaml')
            if repo_name not in save_files:
                save_files[repo_name] = open(save_file, "w")
            LOG.debug("Collecting file %s to file %s" % (filename, save_file))
            save_files[repo_name].writelines(_read_and_format_yaml(filename))
    except Exception as ex:
        raise click.ClickException("Error saving output: %s" % str(ex))
    finally:
        for f in save_files.values():
            f.close()


def collect(site_name, save_location):
    if save_location:
        _collect_to_file(site_name, save_location)
    else:
        _collect_to_stdout(site_name)


def render(site_name, output_stream):
    documents = []
    for filename in util.definition.site_files(site_name):
        with open(filename) as f:
            documents.extend(list(yaml.safe_load_all(f)))

    rendered_documents, errors = util.deckhand.deckhand_render(
        documents=documents)
    err_msg = ''
    if errors:
        for err in errors:
            if isinstance(err, tuple) and len(err) > 1:
                err_msg += ': '.join(err) + '\n'
            else:
                err_msg += str(err) + '\n'
        raise click.ClickException(err_msg)
    yaml.dump_all(rendered_documents, output_stream, default_flow_style=False)


def list_(output_stream):
    """List site names for a given repository."""

    # TODO(felipemonteiro): This should output a formatted table, not rows of
    # data without delimited columns.
    fieldnames = ['site_name', 'site_type', 'repositories']
    writer = csv.DictWriter(
        output_stream, fieldnames=fieldnames, delimiter=' ')
    for site_name in util.files.list_sites():
        params = util.definition.load_as_params(site_name)
        # TODO(felipemonteiro): This is a temporary hack around legacy manifest
        # repositories containing the name of a directory that symbolizes a
        # repository. Once all these manifest repositories migrate over to Git
        # references instead, remove this hack.
        # NOTE(felipemonteiro): The 'revision' information can instead be
        # computed using :func:`process_site_repository` and storing into
        # a configuration via a "set_site_revision" function, for example.
        if 'revision' in params:
            params.pop('revision')
        writer.writerow(params)


def show(site_name, output_stream):
    data = util.definition.load_as_params(site_name)
    data['files'] = list(util.definition.site_files(site_name))
    json.dump(data, output_stream, indent=2, sort_keys=True)

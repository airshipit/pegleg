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

from collections import OrderedDict
import logging
import os

import click
import git
from prettytable import PrettyTable
import yaml
from yaml.constructor import SafeConstructor

from pegleg import config
from pegleg.engine import util
from pegleg.engine.util import files
from pegleg.engine.util.files import add_representer_ordered_dict
from pegleg.engine.util.git import TEMP_PEGLEG_COMMIT_MSG

__all__ = ('collect', 'list_', 'show', 'render')

LOG = logging.getLogger(__name__)


def _read_and_format_yaml(filename):
    with open(filename, 'r') as f:
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
        add_representer_ordered_dict()
        res = yaml.safe_dump(
            get_deployment_data_doc(),
            explicit_start=True,
            explicit_end=True,
            default_flow_style=False)
        # Click isn't splitting these lines correctly, so do it manually
        for line in res.split('\n'):
            click.echo(line)
    except Exception as ex:
        raise click.ClickException("Error printing output: %s" % str(ex))


def _collect_to_file(site_name, save_location):
    """Collects all documents related to ``site_name`` and outputs them to
    the file denoted by ``save_location``.
    """

    files.check_file_save_location(save_location)

    save_files = dict()
    curr_site_repo = files.path_leaf(config.get_site_repo())

    try:
        for repo_base, filename in util.definition.site_files_by_repo(
                site_name):
            repo_name = os.path.normpath(repo_base).split(os.sep)[-1]
            save_file = os.path.join(save_location, repo_name + '.yaml')
            if repo_name not in save_files:
                save_files[repo_name] = open(save_file, 'w')
            LOG.debug("Collecting file %s to file %s", filename, save_file)
            save_files[repo_name].writelines(_read_and_format_yaml(filename))
        add_representer_ordered_dict()
        save_files[curr_site_repo].writelines(
            yaml.safe_dump(
                get_deployment_data_doc(),
                default_flow_style=False,
                explicit_start=True,
                explicit_end=True))
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


def render(site_name, output_stream, validate):
    rendered_documents = get_rendered_docs(site_name, validate=validate)
    rendered_documents.append(get_deployment_data_doc())
    if output_stream:
        files.dump_all(
            rendered_documents,
            output_stream,
            default_flow_style=False,
            explicit_start=True,
            explicit_end=True)
    else:
        add_representer_ordered_dict()
        click.echo(
            yaml.dump_all(
                rendered_documents,
                default_flow_style=False,
                explicit_start=True,
                explicit_end=True))


def get_rendered_docs(site_name, validate=True):
    documents = []
    # Ignore YAML tags, only construct dicts
    SafeConstructor.add_multi_constructor(
        '', lambda loader, suffix, node: None)
    for filename in util.definition.site_files(site_name):
        with open(filename, 'r') as f:
            documents.extend(list(yaml.safe_load_all(f)))

    rendered_documents, errors = util.deckhand.deckhand_render(
        documents=documents, validate=validate)

    if errors:
        err_msg = ''
        for err in errors:
            if isinstance(err, tuple) and len(err) > 1:
                err_msg += ': '.join(err) + '\n'
            else:
                err_msg += str(err) + '\n'
        raise click.ClickException(err_msg)

    return rendered_documents


def list_(output_stream):
    """List site names for a given repository."""

    # Create a table to output site information for all sites for a given repo
    site_table = PrettyTable()
    field_names = ['site_name', 'site_type']
    site_table.field_names = field_names

    for site_name in util.files.list_sites():
        params = util.definition.load_as_params(site_name, *field_names)
        site_table.add_row(list(map(lambda k: params[k], field_names)))
    # Write table to specified output_stream
    msg = site_table.get_string()
    if output_stream:
        files.write(msg + "\n", output_stream)
    else:
        click.echo(msg)


def show(site_name, output_stream):
    data = util.definition.load_as_params(site_name)
    data['files'] = list(util.definition.site_files(site_name))
    # Create a table to output site information for specific site
    site_table = PrettyTable()
    site_table.field_names = ['revision', 'site_name', 'site_type', 'files']
    # TODO(felipemonteiro): Drop support for 'revision' once manifest
    # repositories have removed it altogether.
    if 'revision' in data.keys():
        for file in data['files']:
            site_table.add_row(
                [data['revision'], data['site_name'], data['site_type'], file])
    else:
        for file in data['files']:
            site_table.add_row(
                ["", data['site_name'], data['site_type'], file])
    # Write tables to specified output_stream
    msg = site_table.get_string()
    if output_stream:
        files.write(msg + "\n", output_stream)
    else:
        click.echo(msg)


def get_deployment_data_doc():
    stanzas = {
        files.path_leaf(repo): _get_repo_deployment_data_stanza(repo)
        for repo in config.all_repos()
    }
    return OrderedDict(
        [
            ("schema", "pegleg/DeploymentData/v1"),
            (
                "metadata",
                OrderedDict(
                    [
                        ("schema", "metadata/Document/v1"),
                        ("name", "deployment-version"),
                        (
                            "layeringDefinition",
                            OrderedDict(
                                [("abstract", False), ("layer", "global")])),
                        ("storagePolicy", "cleartext"),
                    ])), ("data", OrderedDict([("documents", stanzas)]))
        ])


def _get_repo_deployment_data_stanza(repo_path):
    try:
        repo = git.Repo(repo_path)
        commit = repo.commit()
        contains_pegleg_commit = TEMP_PEGLEG_COMMIT_MSG in commit.message

        # The repo may not appear dirty if Pegleg has made a temporary commit
        # on top of changed/untracked files, but we know if that temporary
        # commit happened the repo is indeed dirty
        dirty = (repo.is_dirty() or contains_pegleg_commit)

        if contains_pegleg_commit:
            # The commit grabbed above isn't really what we want this data to
            # reflect, because it was a commit made by Pegleg itself.
            # Grab the commit before Pegleg made its temporary commit(s)
            while (TEMP_PEGLEG_COMMIT_MSG in commit.message
                   and len(commit.parents) > 0):
                commit = commit.parents[0]

        # If we're at a particular tag, reference it
        tag = [tag.name for tag in repo.tags if tag.commit == commit]
        if tag:
            tag == ", ".join(tag)
        else:
            # Otherwise just use the branch name
            try:
                tag = repo.active_branch.name
            except TypeError as e:
                if "HEAD is a detached symbolic reference" in str(e):
                    tag = "Detached HEAD"
                else:
                    raise e
        return {"commit": commit.hexsha, "tag": tag, "dirty": dirty}
    except git.InvalidGitRepositoryError:
        return {"commit": "None", "tag": "None", "dirty": "None"}

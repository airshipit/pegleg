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
import logging
import os
import pkg_resources
import yaml

from pegleg import config
from pegleg.engine import util
from pegleg.engine.errorcodes import DOCUMENT_LAYER_MISMATCH
from pegleg.engine.errorcodes import FILE_CONTAINS_INVALID_YAML
from pegleg.engine.errorcodes import FILE_MISSING_YAML_DOCUMENT_HEADER
from pegleg.engine.errorcodes import REPOS_MISSING_DIRECTORIES_FLAG
from pegleg.engine.errorcodes import SCHEMA_STORAGE_POLICY_MISMATCH_FLAG
from pegleg.engine.errorcodes import SECRET_NOT_ENCRYPTED_POLICY

__all__ = ['full']

LOG = logging.getLogger(__name__)

DECKHAND_SCHEMAS = {
    'root': 'schemas/deckhand-root.yaml',
    'metadata/Control/v1': 'schemas/deckhand-metadata-control.yaml',
    'metadata/Document/v1': 'schemas/deckhand-metadata-document.yaml',
}


def full(fail_on_missing_sub_src=False, exclude_lint=None, warn_lint=None):
    messages = []
    # If policy is cleartext and error is added this will put
    # that particular message into the warns list and all others will
    # be added to the error list if SCHEMA_STORAGE_POLICY_MISMATCH_FLAG
    messages.extend(_verify_file_contents())

    # Deckhand Rendering completes without error
    messages.extend(_verify_deckhand_render(fail_on_missing_sub_src))

    # All repos contain expected directories
    messages.extend(_verify_no_unexpected_files())

    errors = []
    warns = []
    for code, message in messages:
        if code in warn_lint:
            warns.append('%s: %s' % (code, message))
        elif code not in exclude_lint:
            errors.append('%s: %s' % (code, message))

    if errors:
        raise click.ClickException('\n'.join(
            ['Linting failed:'] + errors + ['Linting warnings:'] + warns))
    return warns


def _verify_no_unexpected_files():
    expected_directories = set()
    for site_name in util.files.list_sites():
        params = util.definition.load_as_params(site_name)
        expected_directories.update(util.files.directories_for(**params))

    LOG.debug('expected_directories: %s', expected_directories)
    found_directories = util.files.existing_directories()
    LOG.debug('found_directories: %s', found_directories)

    errors = []
    for unused_dir in sorted(found_directories - expected_directories):
        errors.append((REPOS_MISSING_DIRECTORIES_FLAG,
                       '%s exists, but is unused' % unused_dir))

    for missing_dir in sorted(expected_directories - found_directories):
        if not missing_dir.endswith('common'):
            errors.append(
                (REPOS_MISSING_DIRECTORIES_FLAG,
                 '%s was not found, but expected by manifest' % missing_dir))

    return errors


def _verify_file_contents():
    schemas = _load_schemas()

    errors = []
    for filename in util.files.all():
        errors.extend(_verify_single_file(filename, schemas))
    return errors


def _verify_single_file(filename, schemas):
    errors = []
    LOG.debug("Validating file %s." % filename)
    with open(filename) as f:
        if not f.read(4) == '---\n':
            errors.append((FILE_MISSING_YAML_DOCUMENT_HEADER,
                           '%s does not begin with YAML beginning of document '
                           'marker "---".' % filename))
        f.seek(0)
        try:
            documents = list(yaml.safe_load_all(f))
        except Exception as e:
            errors.append((FILE_CONTAINS_INVALID_YAML,
                           '%s is not valid yaml: %s' % (filename, e)))

        for document in documents:
            errors.extend(_verify_document(document, schemas, filename))

    return errors


MANDATORY_ENCRYPTED_TYPES = {
    'deckhand/CertificateAuthorityKey/v1',
    'deckhand/CertificateKey/v1',
    'deckhand/Passphrase/v1',
    'deckhand/PrivateKey/v1',
}


def _verify_document(document, schemas, filename):
    name = ':'.join([
        document.get('schema', ''),
        document.get('metadata', {}).get('name', '')
    ])
    errors = []

    layer = _layer(document)
    if layer is not None and layer != _expected_layer(filename):
        errors.append(
            (DOCUMENT_LAYER_MISMATCH,
             '%s (document %s) had unexpected layer "%s", expected "%s"' %
             (filename, name, layer, _expected_layer(filename))))

    # secrets must live in the appropriate directory, and must be
    # "storagePolicy: encrypted".
    if document.get('schema') in MANDATORY_ENCRYPTED_TYPES:
        storage_policy = document.get('metadata', {}).get('storagePolicy')

        if (storage_policy != 'encrypted'):
            errors.append((SCHEMA_STORAGE_POLICY_MISMATCH_FLAG,
                           '%s (document %s) is a secret, but has unexpected '
                           'storagePolicy: "%s"' % (filename, name,
                                                    storage_policy)))

        if not _filename_in_section(filename, 'secrets/'):
            errors.append((SECRET_NOT_ENCRYPTED_POLICY,
                           '%s (document %s) is a secret, is not stored in a '
                           'secrets path' % (filename, name)))
    return errors


def _verify_deckhand_render(fail_on_missing_sub_src=False):
    sitenames = list(util.files.list_sites())
    documents_by_site = {s: [] for s in sitenames}

    for sitename in sitenames:
        params = util.definition.load_as_params(sitename)
        paths = util.files.directories_for(**params)
        filenames = set(util.files.search(paths))
        for filename in filenames:
            with open(filename) as f:
                documents_by_site[sitename].extend(list(yaml.safe_load_all(f)))

    all_errors = []

    for sitename, documents in documents_by_site.items():
        LOG.debug('Rendering documents for site: %s.', sitename)
        _, errors = util.deckhand.deckhand_render(
            documents=documents,
            fail_on_missing_sub_src=fail_on_missing_sub_src,
            validate=True,
        )
        LOG.debug('Generated %d rendering errors for site: %s.', len(errors),
                  sitename)
        all_errors.extend(errors)

    return list(set(all_errors))


def _layer(data):
    if hasattr(data, 'get'):
        return data.get('metadata', {}).get('layeringDefinition',
                                            {}).get('layer')


def _expected_layer(filename):
    for r in config.all_repos():
        if filename.startswith(r):
            partial_name = filename[len(r):]
            parts = os.path.normpath(partial_name).split(os.sep)
            return parts[0]


def _load_schemas():
    schemas = {}
    for key, filename in DECKHAND_SCHEMAS.items():
        schemas[key] = util.files.slurp(
            pkg_resources.resource_filename('pegleg', filename))
    return schemas


def _filename_in_section(filename, section):
    directory = util.files.directory_for(path=filename)
    if directory is not None:
        rest = filename[len(directory) + 1:]
        return rest is not None and rest.startswith(section)
    else:
        return False

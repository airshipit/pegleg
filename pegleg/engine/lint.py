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
import shutil
import textwrap
import yaml

from prettytable import PrettyTable

from pegleg import config
from pegleg.engine.errorcodes import DOCUMENT_LAYER_MISMATCH
from pegleg.engine.errorcodes import FILE_CONTAINS_INVALID_YAML
from pegleg.engine.errorcodes import FILE_MISSING_YAML_DOCUMENT_HEADER
from pegleg.engine.errorcodes import REPOS_MISSING_DIRECTORIES_FLAG
from pegleg.engine.errorcodes import SCHEMA_STORAGE_POLICY_MISMATCH_FLAG
from pegleg.engine.errorcodes import SECRET_NOT_ENCRYPTED_POLICY
from pegleg.engine import util

__all__ = ['full']

LOG = logging.getLogger(__name__)

DECKHAND_SCHEMAS = {
    'root': 'schemas/deckhand-root.yaml',
    'metadata/Control/v1': 'schemas/deckhand-metadata-control.yaml',
    'metadata/Document/v1': 'schemas/deckhand-metadata-document.yaml',
}


def full(fail_on_missing_sub_src=False, exclude_lint=None, warn_lint=None):
    """Lint all sites in a repository.

    :param bool fail_on_missing_sub_src: Whether to allow Deckhand rendering
        to fail in the absence of a missing substitution source document which
        might be the case in "offline mode".
    :param list exclude_lint: List of lint rules to exclude. See those
        defined in :mod:`pegleg.engine.errorcodes`.
    :param list warn_lint: List of lint rules to warn about. See those
        defined in :mod:`pegleg.engine.errorcodes`.
    :raises ClickException: If a lint check was caught and it isn't contained
        in ``exclude_lint`` or ``warn_lint``.
    :returns: List of warnings produced, if any.

    """

    exclude_lint = exclude_lint or []
    warn_lint = warn_lint or []
    messages = []
    # If policy is cleartext and error is added this will put
    # that particular message into the warns list and all others will
    # be added to the error list if SCHEMA_STORAGE_POLICY_MISMATCH_FLAG
    messages.extend(_verify_file_contents())

    # FIXME(felipemonteiro): Now that we are using revisioned repositories
    # instead of flat directories with subfolders mirroring "revisions",
    # this lint check analyzes ALL the directories (including these
    # no-longer-valid "revision directories") against the new subset of
    # relevant directories. We need to rewrite this check so that it works
    # after site definitions have been refactored to move the manifests
    # under fake repository folders into the common/ folders.
    #
    # messages.extend(_verify_no_unexpected_files())

    # Deckhand rendering completes without error
    messages.extend(
        _verify_deckhand_render(
            fail_on_missing_sub_src=fail_on_missing_sub_src))

    return _filter_messages_by_warn_and_error_lint(
        messages=messages, exclude_lint=exclude_lint, warn_lint=warn_lint)


def site(site_name,
         fail_on_missing_sub_src=False,
         exclude_lint=None,
         warn_lint=None):
    """Lint ``site_name``.

    :param str site_name: Name of site to lint.
    :param bool fail_on_missing_sub_src: Whether to allow Deckhand rendering
        to fail in the absence of a missing substitution source document which
        might be the case in "offline mode".
    :param list exclude_lint: List of lint rules to exclude. See those
        defined in :mod:`pegleg.engine.errorcodes`.
    :param list warn_lint: List of lint rules to warn about. See those
        defined in :mod:`pegleg.engine.errorcodes`.
    :raises ClickException: If a lint check was caught and it isn't contained
        in ``exclude_lint`` or ``warn_lint``.
    :returns: List of warnings produced, if any.

    """

    exclude_lint = exclude_lint or []
    warn_lint = warn_lint or []
    messages = []

    # FIXME(felipemonteiro): Now that we are using revisioned repositories
    # instead of flat directories with subfolders mirroring "revisions",
    # this lint check analyzes ALL the directories (including these
    # no-longer-valid "revision directories") against the new subset of
    # relevant directories. We need to rewrite this check so that it works
    # after site definitions have been refactored to move the manifests
    # under fake repository folders into the common/ folders.
    #
    # messages.extend(_verify_no_unexpected_files(sitenames=[site_name]))

    # If policy is cleartext and error is added this will put
    # that particular message into the warns list and all others will
    # be added to the error list if SCHEMA_STORAGE_POLICY_MISMATCH_FLAG
    messages.extend(_verify_file_contents(sitename=site_name))

    # Deckhand rendering completes without error
    messages.extend(
        _verify_deckhand_render(
            sitename=site_name,
            fail_on_missing_sub_src=fail_on_missing_sub_src))

    return _filter_messages_by_warn_and_error_lint(
        messages=messages, exclude_lint=exclude_lint, warn_lint=warn_lint)


def _filter_messages_by_warn_and_error_lint(*,
                                            messages=None,
                                            exclude_lint=None,
                                            warn_lint=None):
    """Helper that only filters messages depending on whether or not they
    are present in ``exclude_lint`` or ``warn_lint``.

    Bubbles up errors only if the corresponding code for each is **not** found
    in either ``exclude_lint`` or ``warn_lint``. If the code is found in
    ``exclude_lint``, the lint code is ignored; if the code is found in
    ``warn_lint``, the lint is warned about.

    """

    messages = messages or []
    exclude_lint = exclude_lint or []
    warn_lint = warn_lint or []

    errors = []
    warns = []
    # Create tables to output CLI results
    errors_table = PrettyTable()
    errors_table.field_names = ['error_code', 'error_message']
    warnings_table = PrettyTable()
    warnings_table.field_names = ['warning_code', 'warning_message']
    # Calculate terminal size to always make sure that the table output
    # is readable regardless of screen size
    line_length = int(shutil.get_terminal_size().columns / 1.5)
    for code, message in messages:
        if code in warn_lint:
            warns.append('%s: %s' % (code, message))
            warnings_table.add_row([code, textwrap.fill(message, line_length)])
        elif code not in exclude_lint:
            errors.append('%s: %s' % (code, message))
            errors_table.add_row([code, textwrap.fill(message, line_length)])

    if errors:
        raise click.ClickException('Linting failed:\n' +
                                   errors_table.get_string() +
                                   '\nLinting warnings:\n' +
                                   warnings_table.get_string())
    return warns


def _verify_no_unexpected_files(*, sitenames=None):
    sitenames = sitenames or util.files.list_sites()

    expected_directories = set()
    for site_name in sitenames:
        params = util.definition.load_as_params(site_name)
        expected_directories.update(
            util.files.directories_for(
                site_name=params['site_name'], site_type=params['site_type']))
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


def _verify_file_contents(*, sitename=None):
    if sitename:
        files = util.definition.site_files(sitename)
    else:
        files = util.files.all()
    schemas = _load_schemas()

    errors = []
    for filename in files:
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
        documents = []
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


def _verify_deckhand_render(*, sitename=None, fail_on_missing_sub_src=False):
    """Verify Deckhand render works by using all relevant deployment files.

    :returns: List of errors generated during rendering.
    """
    all_errors = []

    if sitename:
        documents_to_render = util.definition.documents_for_site(sitename)
        LOG.debug('Rendering documents for site: %s.', sitename)
        _, errors = util.deckhand.deckhand_render(
            documents=documents_to_render,
            fail_on_missing_sub_src=fail_on_missing_sub_src,
            validate=True,
        )
        LOG.debug('Generated %d rendering errors for site: %s.', len(errors),
                  sitename)
        all_errors.extend(errors)
    else:
        documents_to_render = util.definition.documents_for_each_site()
        for site_name, documents in documents_to_render.items():
            LOG.debug('Rendering documents for site: %s.', site_name)
            _, errors = util.deckhand.deckhand_render(
                documents=documents,
                fail_on_missing_sub_src=fail_on_missing_sub_src,
                validate=True,
            )
            LOG.debug('Generated %d rendering errors for site: %s.',
                      len(errors), site_name)
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

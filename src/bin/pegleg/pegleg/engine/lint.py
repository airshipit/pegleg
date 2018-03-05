import click
import logging
import os
import pkg_resources
import yaml

from pegleg import config
from pegleg.engine import util

SCHEMA_STORAGE_POLICY_MISMATCH_FLAG = 'P001'
DECKHAND_RENDERING_INCOMPLETE_FLAG = 'P002'
REPOS_MISSING_DIRECTORIES_FLAG = 'P003'

__all__ = ['full']

LOG = logging.getLogger(__name__)

DECKHAND_SCHEMAS = {
    'root': 'schemas/deckhand-root.yaml',
    'metadata/Control/v1': 'schemas/deckhand-metadata-control.yaml',
    'metadata/Document/v1': 'schemas/deckhand-metadata-document.yaml',
}


def full(fail_on_missing_sub_src=False, exclude_lint=None, warn_lint=None):
    errors = []
    warns = []

    messages = _verify_file_contents()
    # If policy is cleartext and error is added this will put
    # that particular message into the warns list and all other will
    # be added to the error list if SCHMEA_STORAGE_POLICY_MITCHMATCH_FLAG
    for msg in messages:
        if (SCHEMA_STORAGE_POLICY_MISMATCH_FLAG in warn_lint
                and SCHEMA_STORAGE_POLICY_MISMATCH_FLAG == msg[0]):
            warns.append(msg)
        else:
            errors.append(msg)

    # Deckhand Rendering completes without error
    if DECKHAND_RENDERING_INCOMPLETE_FLAG in warn_lint:
        warns.extend(
            [(DECKHAND_RENDERING_INCOMPLETE_FLAG, x)
             for x in _verify_deckhand_render(fail_on_missing_sub_src)])
    elif DECKHAND_RENDERING_INCOMPLETE_FLAG not in exclude_lint:
        errors.extend(
            [(DECKHAND_RENDERING_INCOMPLETE_FLAG, x)
             for x in _verify_deckhand_render(fail_on_missing_sub_src)])

    # All repos contain expected directories
    if REPOS_MISSING_DIRECTORIES_FLAG in warn_lint:
        warns.extend([(REPOS_MISSING_DIRECTORIES_FLAG, x)
                      for x in _verify_no_unexpected_files()])
    elif REPOS_MISSING_DIRECTORIES_FLAG not in exclude_lint:
        errors.extend([(REPOS_MISSING_DIRECTORIES_FLAG, x)
                       for x in _verify_no_unexpected_files()])

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
            errors.append('%s does not begin with YAML beginning of document '
                          'marker "---".' % filename)
        f.seek(0)
        try:
            documents = yaml.safe_load_all(f)
            for document in documents:
                errors.extend(_verify_document(document, schemas, filename))
        except Exception as e:
            errors.append('%s is not valid yaml: %s' % (filename, e))

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
            ('N/A',
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
            errors.append(('N/A',
                           '%s (document %s) is a secret, is not stored in a '
                           'secrets path' % (filename, name)))
    return errors


def _verify_deckhand_render(fail_on_missing_sub_src=False):

    documents = []

    for filename in util.files.all():
        with open(filename) as f:
            documents.extend(list(yaml.safe_load_all(f)))

    rendered_documents, errors = util.deckhand.deckhand_render(
        documents=documents,
        fail_on_missing_sub_src=fail_on_missing_sub_src,
        validate=True,
    )
    return errors


def _layer(data):
    if hasattr(data, 'get'):
        return data.get('metadata', {}).get('layeringDefinition',
                                            {}).get('layer')


def _expected_layer(filename):
    for r in config.all_repos():
        if filename.startswith(r + "/"):
            partial_name = filename[len(r) + 1:]
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
    rest = filename[len(directory) + 1:]
    return rest is not None and rest.startswith(section)

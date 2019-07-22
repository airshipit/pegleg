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
import itertools
import logging
import os

from pegleg import config
from pegleg.engine.catalog import pki_utility
from pegleg.engine.common import managed_document as md
from pegleg.engine import exceptions
from pegleg.engine import util
from pegleg.engine.util.pegleg_secret_management import PeglegSecretManagement

__all__ = ['PKIGenerator']

LOG = logging.getLogger(__name__)


class PKIGenerator(object):
    """Generates certificates, certificate authorities and keypairs using
    the ``PKIUtility`` class.

    Pegleg searches through a given "site" to derive all the documents
    of kind ``PKICatalog``, which are in turn parsed for information related
    to the above secret types and passed to ``PKIUtility`` for generation.

    These secrets are output to various subdirectories underneath
    ``<site>/secrets/<subpath>``.

    """
    def __init__(
            self, sitename, block_strings=True, author=None, duration=365):
        """Constructor for ``PKIGenerator``.

        :param int duration: Duration in days that generated certificates
            are valid.
        :param str sitename: Site name for which to retrieve documents used for
            certificate and keypair generation.
        :param bool block_strings: Whether to dump out certificate data as
            block-style YAML string. Defaults to true.
        :param str author: Identifying name of the author generating new
            certificates.

        """

        self._sitename = sitename
        self._documents = util.definition.documents_for_site(sitename)
        self._author = author

        self.keys = pki_utility.PKIUtility(
            block_strings=block_strings, duration=duration)
        self.outputs = collections.defaultdict(dict)

        # Maps certificates to CAs in order to derive certificate paths.
        self._cert_to_ca_map = {}

    def generate(self):
        for catalog in util.catalog.iterate(documents=self._documents,
                                            kind='PKICatalog'):
            for ca_name, ca_def in catalog['data'].get(
                    'certificate_authorities', {}).items():
                ca_cert, ca_key = self.get_or_gen_ca(ca_name)

                for cert_def in ca_def.get('certificates', []):
                    document_name = cert_def['document_name']
                    self._cert_to_ca_map.setdefault(document_name, ca_name)
                    cert, key = self.get_or_gen_cert(
                        document_name,
                        ca_cert=ca_cert,
                        ca_key=ca_key,
                        cn=cert_def['common_name'],
                        hosts=_extract_hosts(cert_def),
                        groups=cert_def.get('groups', []))

            for keypair_def in catalog['data'].get('keypairs', []):
                document_name = keypair_def['name']
                self.get_or_gen_keypair(document_name)

        return self._write(config.get_site_repo())

    def get_or_gen_ca(self, document_name):
        kinds = [
            'CertificateAuthority',
            'CertificateAuthorityKey',
        ]
        return self._get_or_gen(self.gen_ca, kinds, document_name)

    def get_or_gen_cert(self, document_name, **kwargs):
        kinds = [
            'Certificate',
            'CertificateKey',
        ]
        return self._get_or_gen(self.gen_cert, kinds, document_name, **kwargs)

    def get_or_gen_keypair(self, document_name):
        kinds = [
            'PublicKey',
            'PrivateKey',
        ]
        return self._get_or_gen(self.gen_keypair, kinds, document_name)

    def gen_ca(self, document_name, **kwargs):
        return self.keys.generate_ca(document_name, **kwargs)

    def gen_cert(self, document_name, *, ca_cert, ca_key, **kwargs):
        ca_cert_data = ca_cert['data']['managedDocument']['data']
        ca_key_data = ca_key['data']['managedDocument']['data']
        return self.keys.generate_certificate(
            document_name, ca_cert=ca_cert_data, ca_key=ca_key_data, **kwargs)

    def gen_keypair(self, document_name):
        return self.keys.generate_keypair(document_name)

    def _get_or_gen(self, generator, kinds, document_name, *args, **kwargs):
        docs = self._find_docs(kinds, document_name)
        if not docs:
            docs = generator(document_name, *args, **kwargs)
        else:
            docs = PeglegSecretManagement(docs=docs)

        # Adding these to output should be idempotent, so we use a dict.

        for wrapper_doc in docs:
            wrapped_doc = wrapper_doc['data']['managedDocument']
            schema = wrapped_doc['schema']
            name = wrapped_doc['metadata']['name']
            self.outputs[schema][name] = wrapper_doc

        return docs

    def _find_docs(self, kinds, document_name):
        schemas = ['deckhand/%s/v1' % k for k in kinds]
        docs = self._find_among_collected(schemas, document_name)
        if docs:
            if len(docs) == len(kinds):
                LOG.debug(
                    'Found docs in input config named %s, kinds: %s',
                    document_name, kinds)
                return docs
            else:
                raise exceptions.IncompletePKIPairError(
                    kinds=kinds, name=document_name)

        else:
            docs = self._find_among_outputs(schemas, document_name)
            if docs:
                LOG.debug(
                    'Found docs in current outputs named %s, kinds: %s',
                    document_name, kinds)
                return docs
        # TODO(felipemonteiro): Should this be a critical error?
        LOG.debug(
            'No docs existing docs named %s, kinds: %s', document_name, kinds)
        return []

    def _find_among_collected(self, schemas, document_name):
        result = []
        for schema in schemas:
            doc = _find_document_by(
                self._documents, schema=schema, name=document_name)
            # If the document wasn't found, then means it needs to be
            # generated.
            if doc:
                result.append(doc)
        return result

    def _find_among_outputs(self, schemas, document_name):
        result = []
        for schema in schemas:
            if document_name in self.outputs.get(schema, {}):
                result.append(self.outputs[schema][document_name])
        return result

    def _write(self, output_dir):
        documents = self.get_documents()
        output_paths = set()

        # First, delete each of the output paths below because we do an append
        # action in the `open` call below. This means that for regeneration
        # of certs, the original paths must be deleted.
        for document in documents:
            output_file_path = md.get_document_path(
                sitename=self._sitename,
                wrapper_document=document,
                cert_to_ca_map=self._cert_to_ca_map)
            output_path = os.path.join(output_dir, 'site', output_file_path)
            # NOTE(felipemonteiro): This is currently an entirely safe
            # operation as these files are being removed in the temporarily
            # replicated versions of the local repositories.
            if os.path.exists(output_path):
                os.remove(output_path)

        # Next, generate (or regenerate) the certificates.
        for document in documents:
            output_file_path = md.get_document_path(
                sitename=self._sitename,
                wrapper_document=document,
                cert_to_ca_map=self._cert_to_ca_map)
            output_path = os.path.join(output_dir, 'site', output_file_path)
            dir_name = os.path.dirname(output_path)

            if not os.path.exists(dir_name):
                LOG.debug('Creating secrets path: %s', dir_name)
                os.makedirs(os.path.abspath(dir_name))

            # Encrypt the document
            document['data']['managedDocument']['metadata']['storagePolicy']\
                = 'encrypted'
            document = PeglegSecretManagement(
                docs=[document]).get_encrypted_secrets()[0][0]

            util.files.dump(
                document,
                output_path,
                flag='a',
                default_flow_style=False,
                explicit_start=True,
                indent=2)

            output_paths.add(output_path)
        return output_paths

    def get_documents(self):
        return list(
            itertools.chain.from_iterable(
                v.values() for v in self.outputs.values()))


def get_host_list(service_names):
    service_list = []
    for service in service_names:
        parts = service.split('.')
        for i in range(len(parts)):
            service_list.append('.'.join(parts[:i + 1]))
    return service_list


def _extract_hosts(cert_def):
    hosts = cert_def.get('hosts', [])
    hosts.extend(get_host_list(cert_def.get('kubernetes_service_names', [])))
    return hosts


def _find_document_by(documents, **kwargs):
    try:
        return next(_iterate(documents, **kwargs))
    except StopIteration:
        return None


def _iterate(documents, *, kind=None, schema=None, labels=None, name=None):
    if kind is not None:
        if schema is not None:
            raise AssertionError('Logic error: specified both kind and schema')
        schema = 'promenade/%s/v1' % kind

    for document in documents:
        if _matches_filter(document, schema=schema, labels=labels, name=name):
            yield document


def _matches_filter(document, *, schema, labels, name):
    matches = True

    if md.is_managed_document(document):
        document = document['data']['managedDocument']
    else:
        document_schema = document['schema']
        if document_schema in md.SUPPORTED_SCHEMAS:
            # Can't use the filter value as they might not be an exact match.
            document_metadata = document['metadata']
            document_labels = document_metadata.get('labels', {})
            document_name = document_metadata['name']
            LOG.warning(
                'Detected deprecated unmanaged document during PKI '
                'generation. Details: schema=%s, name=%s, labels=%s.',
                document_schema, document_labels, document_name)

    if schema is not None and not document.get('schema',
                                               '').startswith(schema):
        matches = False

    if labels is not None:
        document_labels = _mg(document, 'labels', [])
        for key, value in labels.items():
            if key not in document_labels:
                matches = False
            else:
                if document_labels[key] != value:
                    matches = False

    if name is not None:
        if _mg(document, 'name') != name:
            matches = False

    return matches


def _mg(document, field, default=None):
    return document.get('metadata', {}).get(field, default)

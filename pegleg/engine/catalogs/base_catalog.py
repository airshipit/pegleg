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

from abc import ABC
import logging
import re

from pegleg import config
from pegleg.engine.exceptions import PassphraseCatalogNotFoundException
from pegleg.engine.util import definition
from pegleg.engine.util import git

LOG = logging.getLogger(__name__)

__all__ = ['BaseCatalog']


class BaseCatalog(ABC):
    """Abstract Base Class for all site catalogs."""

    def __init__(self, kind, sitename, documents=None):
        """
        Search for site catalog of the specified ``kind`` among the site
        documents, and capture the catalog common metadata.

        :param str kind: The catalog kind
        :param str sitename: Name of the environment
        :param list documents: Optional list of site documents. If not
        present, the constructor will use the ``site_name` to lookup the list
        of site documents.
        """
        self._documents = documents or definition.documents_for_site(sitename)
        self._site_name = sitename
        self._catalog_path = []
        self._kind = kind
        self._catalog_docs = list()
        for document in self._documents:
            schema = document.get('schema')
            if schema == 'pegleg/%s/v1' % kind:
                self._catalog_docs.append(document)
            elif schema == 'promenade/%s/v1' % kind:
                LOG.warning('The schema promenade/%s/v1 is deprecated. Use '
                            'pegleg/%s/v1 instead.', kind, kind)
                self._catalog_docs.append(document)

    @property
    def site_name(self):
        return self._site_name

    @property
    def catalog_path(self):
        if not self._catalog_path:
            self._set_catalog_path()
        return self._catalog_path

    def _set_catalog_path(self):
        repo_name = git.repo_url(config.get_site_repo())
        catalog_name = self._get_document_name('{}.yaml'.format(self._kind))
        for file_path in definition.site_files(self.site_name):
            if file_path.endswith(catalog_name):
                self._catalog_path.append(file_path)
        if not self._catalog_path:
            # Cound not find the Catalog for this generated passphrase
            # raise an exception.
            LOG.error('Catalog path: {} was not found in repo: {}'.format(
                catalog_name, repo_name))
            raise PassphraseCatalogNotFoundException()

    def _get_document_name(self, name):
        s1 = re.sub('(.)([A-Z][a-z]+)', r'\1-\2', name)
        return re.sub('([a-z0-9])([A-Z])', r'\1-\2', s1).lower()

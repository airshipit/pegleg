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
from pytest import mark

from pegleg.engine.util import definition


class TestSiteDefinitionHelpers(object):
    def _test_documents_for_site(self, sitename):
        documents = definition.documents_for_site(sitename)
        global_documents = []
        site_documents = []

        for document in documents:
            name = document["metadata"]["name"]
            # Assert that the document is either global level or a relevant
            # site document.
            assert name.startswith("global") or name.startswith(sitename)

            if name.startswith("global"):
                global_documents.append(document)
            elif name.startswith(sitename):
                site_documents.append(document)
            else:
                raise AssertionError(
                    "Unexpected document retrieved by "
                    "`documents_for_site`: %s" % document)

        # Assert that documents from both levels appear.
        assert global_documents
        assert site_documents

        return global_documents + site_documents

    def test_documents_for_site(self, temp_deployment_files):
        self._test_documents_for_site("cicd")
        self._test_documents_for_site("lab")

    def test_documents_for_each_site(self, temp_deployment_files):
        documents_by_site = definition.documents_for_each_site()
        sort_func = lambda x: x['metadata']['name']

        # Validate that both expected site documents are found.
        assert 2 == len(documents_by_site)
        assert "cicd" in documents_by_site
        assert "lab" in documents_by_site

        cicd_documents = self._test_documents_for_site("cicd")
        lab_documents = self._test_documents_for_site("lab")

        # Validate that each set of site documents matches the same set of
        # documents returned by ``documents_for_site`` for that site.
        assert (
            sorted(cicd_documents, key=sort_func) == sorted(
                documents_by_site["cicd"], key=sort_func))
        assert (
            sorted(lab_documents, key=sort_func) == sorted(
                documents_by_site["lab"], key=sort_func))

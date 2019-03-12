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

import json
import logging
import uuid

import yaml

from pegleg.engine.exceptions import PeglegBaseException
from pegleg.engine.util import files
from pegleg.engine.util.pegleg_secret_management import PeglegSecretManagement

from shipyard_client.api_client.shipyard_api_client import ShipyardClient
from shipyard_client.api_client.shipyardclient_context import \
    ShipyardClientContext

LOG = logging.getLogger(__name__)


class AuthValuesError(PeglegBaseException):
    """Shipyard authentication failed. """

    def __init__(self, *, diagnostic):
        self.diagnostic = diagnostic


class DocumentUploadError(PeglegBaseException):
    """Exception occurs while uploading documents"""

    def __init__(self, message):
        self.message = message


class ShipyardHelper(object):
    """
    A helper class for Shipyard. It performs the following operation:
    1. Validates the authentication parameters required for Keystone
    2. Uploads the document to Shipyard buffer
    3. Commits the document
    4. Formats response from Shipyard api_client
    """

    def __init__(self, context):
        """
        Initializes params to be used by Shipyard

        :param context: ShipyardHelper context object that contains
                        params for initializing ShipyardClient with
                        correct client context and the site_name.
        """
        self.ctx = context
        self.api_parameters = self.ctx.obj['API_PARAMETERS']
        self.auth_vars = self.api_parameters.get('auth_vars')
        self.context_marker = self.ctx.obj['context_marker']
        if self.context_marker is None:
            self.context_marker = str(uuid.uuid4())
            LOG.debug("context_marker is %s", self.context_marker)
        self.site_name = self.ctx.obj['site_name']
        self.client_context = ShipyardClientContext(
            self.auth_vars, self.context_marker)
        self.api_client = ShipyardClient(self.client_context)

    def upload_documents(self):
        """Uploads documents to Shipyard """

        collected_documents = files.collect_files_by_repo(self.site_name)

        LOG.info("Uploading %d collection(s) ", len(collected_documents))
        for idx, document in enumerate(collected_documents):
            # Append flag is not required for the first
            # collection being uploaded to Shipyard. It
            # is needed for subsequent collections.
            if idx == 0:
                buffer_mode = None
            else:
                buffer_mode = 'append'

            # Decrypt the documents if encrypted
            pegleg_secret_mgmt = PeglegSecretManagement(
                docs=collected_documents[document])
            decrypted_documents = pegleg_secret_mgmt.get_decrypted_secrets()
            data = yaml.safe_dump_all(decrypted_documents)

            try:
                self.validate_auth_vars()
                # Get current buffer status.
                response = self.api_client.get_configdocs_status()
                buff_stat = response.json()
                # If buffer is empty then proceed with existing buffer value
                # else pass the 'replace' flag.
                for stat in range(len(buff_stat)):
                    if (buff_stat[stat]['new_status'] != 'unmodified' and
                            buffer_mode != 'append'):
                        buffer_mode = 'replace'
                resp_text = self.api_client.post_configdocs(
                    collection_id=document,
                    buffer_mode=buffer_mode,
                    document_data=data
                )

            except AuthValuesError as ave:
                resp_text = "Error: {}".format(ave.diagnostic)
                raise DocumentUploadError(resp_text)
            except Exception as ex:
                resp_text = (
                    "Error: Unable to invoke action due to: {}"
                    .format(str(ex)))
                LOG.debug(resp_text, exc_info=True)
                raise DocumentUploadError(resp_text)

            # FIXME: Standardize status_code in Deckhand to avoid this
            # workaround.
            code = 0
            if hasattr(resp_text, 'status_code'):
                code = resp_text.status_code
            elif hasattr(resp_text, 'code'):
                code = resp_text.code
            if code >= 400:
                if hasattr(resp_text, 'content'):
                    raise DocumentUploadError(resp_text.content)
                else:
                    raise DocumentUploadError(resp_text)
            else:
                output = self.formatted_response_handler(resp_text)
                LOG.info("Uploaded document in buffer %s ", output)

        # Commit in the last iteration of the loop when all the documents
        # have been pushed to Shipyard buffer.
        if idx == len(collected_documents) - 1:
            return self.commit_documents()

    def commit_documents(self):
        """Commit Shipyard buffer documents """

        LOG.info("Commiting Shipyard buffer documents")

        try:
            resp_text = self.formatted_response_handler(
                self.api_client.commit_configdocs()
            )
        except Exception as ex:
            resp_text = (
                "Error: Unable to invoke action due to: {}".format(str(ex)))
            raise DocumentUploadError(resp_text)
        return resp_text

    def validate_auth_vars(self):
        """Checks that the required authorization varible have been entered"""
        required_auth_vars = ['auth_url']
        err_txt = []
        for var in required_auth_vars:
            if self.auth_vars[var] is None:
                err_txt.append(
                    'Missing the required authorization variable: '
                    '--os-{}'.format(var.replace('_', '-')))
        if err_txt:
            for var in self.auth_vars:
                if (self.auth_vars.get(var) is None and
                        var not in required_auth_vars):
                    err_txt.append('- Also not set: --os-{}'.format(
                        var.replace('_', '-')))
            raise AuthValuesError(diagnostic='\n'.join(err_txt))

    def formatted_response_handler(self, response):
        """Base format handler for either json or yaml depending on call"""
        call = response.headers['Content-Type']
        if 'json' in call:
            try:
                return json.dumps(response.json(), indent=4)
            except ValueError:
                return (
                    "This is not json and could not be printed as such. \n" +
                    response.text
                )

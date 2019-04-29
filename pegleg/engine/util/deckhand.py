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


from deckhand.engine import document_validation
from deckhand.engine import layering
from deckhand import errors as dh_errors

from pegleg.engine.errorcodes import DECKHAND_DUPLICATE_SCHEMA
from pegleg.engine.errorcodes import DECKHAND_RENDER_EXCEPTION


def load_schemas_from_docs(documents):
    '''
    Fills the cache of known schemas from the document set
    '''

    errors = []
    SCHEMA_SCHEMA = "deckhand/DataSchema/v1"

    schema_set = dict()
    for document in documents:
        if document.get('schema', '') == SCHEMA_SCHEMA:
            name = document['metadata']['name']
            if name in schema_set:
                errors.append((DECKHAND_DUPLICATE_SCHEMA,
                               'Duplicate schema specified for: %s' % name))

            schema_set[name] = document['data']

    return schema_set, errors


def deckhand_render(documents=None,
                    fail_on_missing_sub_src=False,
                    validate=True):
    documents = documents or []
    errors = []
    rendered_documents = []

    schemas, schema_errors = load_schemas_from_docs(documents)
    errors.extend(schema_errors)

    try:
        deckhand_eng = layering.DocumentLayering(
            documents,
            fail_on_missing_sub_src=fail_on_missing_sub_src,
            validate=validate)
        rendered_documents = [dict(d) for d in deckhand_eng.render()]
        if validate:
            validator = document_validation.DocumentValidation(
                rendered_documents)
            results = validator.validate_all()
            for result in results:
                if result['errors']:
                    errors.append(
                        (DECKHAND_RENDER_EXCEPTION,
                         'During rendering Deckhand was unable to validate '
                         'the following document, details: %s.' % (
                             result['errors'])))
    except dh_errors.DeckhandException as e:
        errors.append(
            (DECKHAND_RENDER_EXCEPTION,
             'An unknown Deckhand exception occurred while trying'
             ' to render documents: %s. Details: %s.' % (str(e),
                                                         e.error_list)))

    return rendered_documents, errors

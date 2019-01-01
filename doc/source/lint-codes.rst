..
  Copyright 2018 AT&T Intellectual Property.
  All Rights Reserved.

  Licensed under the Apache License, Version 2.0 (the "License"); you may
  not use this file except in compliance with the License. You may obtain
  a copy of the License at

      http://www.apache.org/licenses/LICENSE-2.0

  Unless required by applicable law or agreed to in writing, software
  distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
  WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
  License for the specific language governing permissions and limitations
  under the License.

.. _lint-codes:

Lint Codes
==========

Overview
--------

Below are the lint codes that are used by the :ref:`lint <linting>` Pegleg
CLI command.

Codes
-----

* P001 - Document has storagePolicy cleartext (expected is encrypted) yet
  its schema is a mandatory encrypted type.

  Where mandatory encrypted schema type is one of:

  * ``deckhand/CertificateAuthorityKey/v1``
  * ``deckhand/CertificateKey/v1``
  * ``deckhand/Passphrase/v1``
  * ``deckhand/PrivateKey/v1``

  See the `Deckhand Utility Document Kinds`_ documentation for more
  information.

* P003 - All repos contain expected directories.
* P004 - Duplicate Deckhand `DataSchema`_ document detected.
* P005 - Deckhand rendering exception.
* P006 - YAML file missing document header (``---``).
* P007 - YAML file is not valid YAML.
* P008 - Document ``metadata.layeringDefinition.layer`` does not match its
  location in the site manifests tree (e.g. document with ``site`` layer should
  be found in folder named ``site``).
* P009 - Document found in ``secrets`` folder in site manifests repository
  but doesn't have ``storagePolicy: encrypted`` set.
* P010 - Site folder in manifests repository is missing
  :file:`site-definition.yaml`
* P011 - :file:`site-definition.yaml` failed Pegleg schema validation.

.. _DataSchema: https://airship-deckhand.readthedocs.io/en/latest/document-types.html?highlight=dataschema#dataschema
.. _Deckhand Utility Document Kinds: https://airship-deckhand.readthedocs.io/en/latest/users/document-types.html#provided-utility-document-kinds

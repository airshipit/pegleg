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

.. _pegleg-document-types:

Pegleg Document Types
=====================

Overview
--------

Pegleg is not only the custodian of deployment manifests that handles
responsibilities such as aggregation and linting, but is also the author of
certain `Deckhand-formatted`_ manifests. These manifests are generated via
``Catalog`` classes.

.. todo::

  Provide documentation for what Catalog classes are.

Documents
---------

Pegleg generates or ingests each of the documents below, each identified by
its schema.

.. _pegleg-managed-document:

``pegleg/PeglegManagedDocument/v1``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Pegleg both generates and ingests this type of document. A
``PeglegManagedDocument`` can have one or both of the following data elements:

* ``generated``
* ``encrypted``

A ``PeglegManagedDocument`` serves as a wrapper around other documents, and the
wrapping serves to capture additional metadata that is necessary, but
separate from the managed document proper.

The managed document data lives in the ``data.managedDocument`` portion
of a ``PeglegManagedDocument``.

Generated
~~~~~~~~~

If a ``PeglegManagedDocument`` is ``generated``, then its contents have been
created by Pegleg, and it thus includes provenance information per this
example::

  schema: pegleg/PeglegManagedDocument/v1
  metadata:
    name: matches-document-name
    schema: deckhand/Document/v1
    labels:
      matching: wrapped-doc
    layeringDefinition:
      abstract: true
      # Pegleg will initially support generation at site level only
      layer: site
    storagePolicy: encrypted
  data:
    generated:
      at: <timestamp>
      by: <author>
      specifiedBy:
        repo: <...>
        reference: <git ref-head or similar>
        path: <PKICatalog/PassphraseCatalog details>
    managedDocument:
      schema: <as appropriate for wrapped document>
      metadata:
        storagePolicy: encrypted
        schema: <as appropriate for wrapped document>
        <metadata from parent PeglegManagedDocument>
        <any other metadata as appropriate>
      data: <generated data>

Encrypted
~~~~~~~~~

If a ``PeglegManagedDocument`` is ``encrypted``, then its contents have been
encrypted by Pegleg, and it thus includes provenance information per this
example::

  schema: pegleg/PeglegManagedDocument/v1
  metadata:
    name: matches-document-name
    schema: deckhand/Document/v1
    labels:
      matching: wrapped-doc
    layeringDefinition:
      abstract: false
      layer: matching-wrapped-doc
    storagePolicy: encrypted
  data:
    encrypted:
      at: <timestamp>
      by: <author>
    managedDocument:
      schema: <as appropriate for wrapped document>
      metadata:
        storagePolicy: encrypted
        schema: <as appropriate for wrapped document>
        <metadata from parent PeglegManagedDocument>
        <any other metadata as appropriate>
      data: <encrypted string blob>

Note that this ``encrypted`` has a different purpose than the Deckhand
``storagePolicy: encrypted`` `metadata`_, which indicates an *intent* for
Deckhand to store a document encrypted at rest in the cluster. The two can be
used together to ensure security. If a document is marked as
``storagePolicy: encrypted``, then automation may validate that it is only
persisted (e.g. to a Git repository) if it is in fact encrypted within
a ``PeglegManagedDocument``.

Generated & Encrypted
~~~~~~~~~~~~~~~~~~~~~

A ``PeglegManagedDocument`` that is both generated via a ``Catalog``, and
encrypted (as specified by the ``Catalog``) will contain both ``generated`` and
``encrypted`` stanzas.

Supported Managed Documents
~~~~~~~~~~~~~~~~~~~~~~~~~~~

Supported managed document schemas include one of the following
`Deckhand schemas`_:

* Certificates:

  * ``deckhand/Certificate/v1``
  * ``deckhand/CertificateKey/v1``

* Certificate Authorities:

  * ``deckhand/CertificateAuthority/v1``
  * ``deckhand/CertificateAuthorityKey/v1``

* Keypairs:

  * ``deckhand/PrivateKey/v1``
  * ``deckhand/PublicKey/v1``

.. _Deckhand-formatted: https://airship-deckhand.readthedocs.io/en/latest/users/documents.html
.. _metadata: https://airship-deckhand.readthedocs.io/en/latest/users/encryption.html
.. _Deckhand schemas: https://airship-deckhand.readthedocs.io/en/latest/users/document-types.html#provided-utility-document-kinds

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

.. _pki:

Public Key Infrastructure (PKI) Catalog
=======================================

Configuration for certificate and keypair generation in the cluster.  The
``pegleg secrets generate certificates`` command will read all ``PKICatalog``
documents and either find pre-existing certificates/keys, or generate new ones
based on the given definition.

Dependencies
------------

Pegleg's PKI Catalog depends on `CloudFlare's PKI/TLS toolkit`_, which is
installed as a part of Pegleg's `Dockerfile`_.

.. _sample-pki-catalog-yaml:

Sample Document
---------------

Here is a sample document:

.. literalinclude:: ../../../site_yamls/site/pki-catalog.yaml

Certificate Authorities
-----------------------

The data in the ``certificate-authorities`` key is used to generate
certificates for each authority and node.

Each certificate authority requires essential host-specific information for
each node.

.. _CloudFlare's PKI/TLS toolkit: https://github.com/cloudflare/cfssl
.. _Dockerfile: https://github.com/openstack/airship-pegleg/blob/master/images/pegleg/Dockerfile

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

Document Fundamentals
=====================

The definition of a site consists of a set of small YAML documents that
are managed by _Deckhand http://deckhand.readthedocs.io/en/latest/. Each
document is identified by a ``schema`` top-level key and the ``metadata.name``
value that uniquely identifies a particular document of the type ``schema``.
Deckhand provides functionality allowing documents to be authored such that
data from multiple documents can be merged.

    * Abstact vs Concrete - Documents define a value in ``metadata.layeringDefinition.abstract`` to
      determine if a document is abstract (a value of ``true``) or concrete (a value of ``false``).
      When calling the ``/revisions/{id}/rendered-documents`` API, only concrete documents are returned.
    * Layering - Document _layering http://deckhand.readthedocs.io/en/latest/layering.html is used
      for whole documents that have known defaults but may need to be transformed in specific instances.
    * Substitution - Data _substitution http://deckhand.readthedocs.io/en/latest/substitution.html is
      used for extracting particular values from a document's data section (whole or in-part) and
      inserting that data into a destination document (at the root of the data section or deeper
      into a document).

Shared Documents
================

Secrets
-------

Several generic document
_types http://deckhand.readthedocs.io/en/latest/document_types.html#provided-utility-document-kinds
exist to support storing sensitive data encrypted.

These must be utilized for all data considered sensitive.

Global Catalogue Documents
--------------------------

`Deckhand`_'s layering functionality can be utilized in several ways, i.e site
definitions. At the ``global`` layer there will be several documents providing
different configurations for an object or service. Each of these will be
abstract documents. They can be incorporated into a particular site definition
by creating a concrete child document in the ``site`` layer that selects the
correct ``global`` parent. The child can then do further customization on the
configuration if needed.

As a best practice, ``global`` level documents using the catalog pattern
should utilize the layering labels ``component`` and ``configuration`` to
provide a consistent method for children documents select the correct parent.
The below example shows a set  of documents for two configuration options for
OpenStack Keystone: one using local SQL-backed identity stores and one using
an LDAP backend. A site definition can then select and customize the appropriate
option.

When using a catalogue document, it is important to review that document
to ensure you understand all the requirements for it.

  * Abstract documents are not required to be fully formed, so selecting
    a catalogue document may require the child document to add data so
    the document passes validation. In the below example, the child document
    adds several required fields to the catalogue Chart: ``chart_name``,
    ``release``, and ``namespace``.
  * A catalogue document may define substitutions with the expectation
    that the substitution source documents are defined at a lower layer.
    In the example below, all of the required credentials in the chart
    are defined as substitutions in the ``global`` catalogue document,
    but the source documents for the substitutions are defined in the
    ``site`` layer.

This catalogue pattern can also be utilized for the ``type`` layer
if needed.

.. _Deckhand: https://deckhand.readthedocs.io

Global Layer
------------

.. code-block:: yaml

    ---
    schema: armada/Chart/v1
    metadata:
      schema: metadata/Document/v1
      name: ldap-backed-keystone
      labels:
        component: keystone
        configuration: ldap-backed
      layeringDefinition:
        abstract: true
        layer: global
      storagePolicy: cleartext
      substitutions:
        - src:
            schema: deckhand/Passphrase/v1
            name: keystone_admin_password
            path: .
          dest:
            path: .values.endpoints.identity.auth.admin.password
        - src:
            schema: deckhand/Passphrase/v1
            name: mariadb_admin_password
            path: .
          dest:
            path: .values.endpoints.oslo_db.auth.admin.password
        - src:
            schema: deckhand/Passphrase/v1
            name: mariadb_keystone_password
            path: .
          dest:
            path: .values.endpoints.oslo_db.auth.user.password
        - src:
            schema: pegleg/SoftwareVersions/v1
            name: software-versions
            path: .charts.ucp.keystone
          dest:
            path: .source
        - src:
            schema: pegleg/StringValue/v1
            name: ldap_userid
            src: .
          dest:
            path: .values.conf.ks_domains.cicd.identity.ldap.user
            pattern: '(^USERID)'
        - src:
            schema: deckhand/Passphrase/v1
            name: ldap_userid_password
            path: .
          dest:
            path: .values.conf.ks_domain.cicd.identity.ldap.password
    data:
      install:
        no_hooks: false
      upgrade:
        no_hooks: false
      pre:
        delete:
          - type: job
            labels:
              job-name: keystone-db-sync
          - type: job
            labels:
              job-name: keystone-db-init
      post:
        delete: []
        create: []
      values:
        conf:
          keystone:
            identity:
              driver: sql
              default_domain_id: default
              domain_specific_drivers_enabled: True
              domain_configurations_from_database: True
              domain_config_dir: /etc/keystonedomains
          ks_domains:
            cicd:
              identity:
                driver: ldap
                ldap:
                  url: "ldap://your-ldap-server.example.com"
                  user: "USERID@example.com"
                  password: USERID_PASSWORD_REPLACEME
                  suffix: "dc=example,dc=com"
                  query_scope: sub
                  page_size: 1000
                  user_tree_dn: "DC=example,DC=com"
                  user_objectclass: user
                  user_name_attribute: sAMAccountName
                  user_mail_attribute: mail
                  user_enabled_attribute: userAccountControl
                  user_enabled_mask: 2
                  user_enabled_default: 512
                  user_attribute_ignore: "default_project_id,tenants,projects,password"
        replicas: 2
        labels:
          node_selector_key: ucp-control-plane
          node_selector_value: enabled
    ...
    ---
    schema: armada/Chart/v1
    metadata:
      schema: metadata/Document/v1
      name: sql-backed-keystone
      labels:
        component: keystone
        configuration: sql-backed
      layeringDefinition:
        abstract: true
        layer: global
      substitutions:
        - src:
            schema: deckhand/Passphrase/v1
            name: keystone_admin_password
            path: .
          dest:
            path: .values.endpoints.identity.auth.admin.password
        - src:
            schema: deckhand/Passphrase/v1
            name: mariadb_admin_password
            path: .
          dest:
            path: .values.endpoints.oslo_db.auth.admin.password
        - src:
            schema: deckhand/Passphrase/v1
            name: mariadb_keystone_password
            path: .
          dest:
            path: .values.endpoints.oslo_db.auth.user.password
        - src:
            schema: pegleg/SoftwareVersions/v1
            name: software-versions
            path: .charts.ucp.keystone
          dest:
            path: .source
    data:
      timeout: 300
      install:
        no_hooks: false
      upgrade:
        no_hooks: false
        pre:
          delete:
            - name: keystone-bootstrap
              type: job
              labels:
                application: keystone
                component: bootstrap
            - name: keystone-credential-setup
              type: job
              labels:
                application: keystone
                component: credential-setup
            - name: keystone-db-init
              type: job
              labels:
                application: keystone
                component: db-init
            - name: keystone-db-sync
              type: job
              labels:
                application: keystone
                component: db-sync
            - name: keystone-fernet-setup
              type: job
              labels:
                application: keystone
                component: fernet-setup
      values: {}
      source: {}
    ...

Site Layer
----------

.. code-block:: yaml

    ---
    schema: armada/Chart/v1
    metadata:
      schema: metadata/Document/v1
      name: ucp-helm-toolkit
      layeringDefinition:
        abstract: false
        layer: site
      substitutions:
        - src:
            schema: pegleg/SoftwareVersions/v1
            name: software-versions
            path: .charts.ucp.helm-toolkit
          dest:
            path: .source
    data:
      chart_name: ucp-helm-toolkit
      release: ucp-helm-toolkit
      namespace: ucp
      timeout: 100
      values: {}
      source: {}
      dependencies: []
    ...
    ---
    schema: armada/Chart/v1
    metadata:
      schema: metadata/Document/v1
      name: ucp-keystone
      layeringDefinition:
        abstract: false
        layer: site
        parentSelector:
          component: keystone
          configuration: ldap-backed
        actions:
          - method: merge
            path: .
    data:
      chart_name: ucp-keystone
      release: ucp-keystone
      namespace: ucp
      dependencies:
        - ucp-helm-toolkit
    ...
    ---
    schema: deckhand/Passphrase/v1
    metadata:
      schema: metadata/Document/v1
      name: ldap_userid_password
      storagePolicy: encrypted
    data: a-secret-password
    ...
    ---
    schema: deckhand/Passphrase/v1
    metadata:
      schema: metadata/Document/v1
      name: keystone_admin_password
      storagePolicy: encrypted
    data: a-secret-password
    ...
    ---
    schema: deckhand/Passphrase/v1
    metadata:
      schema: metadata/Document/v1
      name: mariadb_admin_password
      storagePolicy: encrypted
    data: a-secret-password
    ...
    ---
    schema: deckhand/Passphrase/v1
    metadata:
      schema: metadata/Document/v1
      name: mariadb_keystone_password
      storagePolicy: encrypted
    data: a-secret-password
    ...
    ---
    schema: pegleg/StringValue/v1
    metadata:
      schema: metadata/Document/v1
      name: keystone_ldap_userid
      storagePolicy: cleartext
    data: myuser
    ...

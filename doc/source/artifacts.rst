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

Definition Artifact Layout
==========================

The definition artifacts are stored in the below directory structure. This
structure is used only to assist humans in maintaining the data. When the
documents are consumed by the Airship services, they are viewed as a flat set
of all documents.::

  deployment_files/deployment_files
   |- /global
   |    |- /common
   |    |    |- {definition library}
   |    |- /v1.0
   |         |- {definition library}
   |- /type
   |    |- /production
   |    |    |- /v1.0
   |    |         |- {definition library}
   |    |- /cicd
   |    |    |- /v1.0
   |    |         |- {definition library}
   |    |- /labs
   |         |- /v1.0
   |              |- {definition library}
   |- /site
        |- /{sitename}
             |- site_definition.yaml
             |- {definition library}

The root-level listings of ``global``, ``type`` and ``site``
are the layers as listed in the `Deckhand LayeringPolicy`_
document. The process of choosing the definition libraries
to compose the actual design for a site is described below.

.. _Deckhand LayeringPolicy: https://airship-deckhand.readthedocs.io/en/latest/overview.html#layering

site_definition.yaml
--------------------

The site_definition.yaml file is what selects the definition libraries
to use for a site. Additional metadata can be added to this file as needed
to meet requirements.::

    ---
    schema: pegleg/SiteDefinition/v1
    metadata:
      layeringDefinition:
        abstract: false
        layer: 'site'
      name: 'mtn13b.1'
      schema: metadata/Document/v1
      storagePolicy: cleartext
    data:
      site_type: 'cicd'
      repositories:  # Optional field.
        global:
          revision: 47676764d3935e4934624bf9593e9115984fe668
          url: ssh://REPO_USERNAME@<git_url>:29418/global-manifests.git
        secrets:
          revision: master
          url: ssh://REPO_USERNAME@<git_url>:29418/security-manifests.git

The ``repositories`` field (optional) maps default authentication information
for each of the manifests repositories supported, for example:

* global
* secrets
* site

Each of the above fields must have 2 pieces of information:

* ``revision`` (required) - specifies a valid :ref:`git-reference`.

* ``url`` (required) - specifies the repository remote path. Consists of the
  following required segments:

  * protocol - http, https, or ssh.
  * REPO_USERNAME - must be included for ssh only. Can be overridden with the
    CLI via :ref:`command-line-repository-overrides`.
  * port - e.g. 29418 - must be included for ssh only.
  * repository name

Self-Contained Repository
^^^^^^^^^^^^^^^^^^^^^^^^^

Note that if the ``repositories`` field is omitted, then this implies that the
repository contains **all** the manifests required for site deployment. One
such example is `Airship in a Bottle`_ which hosts all the manifests required
for deploying a minimum OpenStack development environment.

Please see the :ref:`related CLI documentation <self-contained-repo>` for
information on how to issue relevant commands.

Definition Library Layout
=========================

The definition library layout is replicated in each location that the
site definition contains a set of documents.::

    {library root}
      |- /schemas
      |    |- /{namespace}
      |        |- /{kind}
      |            |- {version}.yaml
      |
      |- /profiles
      |    |- /hardware
      |    |- /host
      |
      |- /pki
      |    |- kubernetes-nodes.yaml
      |
      |- /secrets
      |    |- /certifcate-authorities
      |    |- /certificates
      |    |- /keypairs
      |    |- /passphrases
      |
      |- /software
      |    |- /charts
      |    |    |- /{chart collection}
      |    |    |    |- dependencies.yaml
      |    |    |    |- /{chartgroup}
      |    |    |         |- chart-group.yaml
      |    |    |         |- {chart1}.yaml
      |    |    |         |- {chart2}.yaml
      |    |    |
      |    |    |- /{chart collection}
      |    |         |- dependencies.yaml
      |    |         |- /{chartgroup}
      |    |              |- chart-group.yaml
      |    |              |- {chart1}.yaml
      |    |              |- {chart2}.yaml
      |    |
      |    |- /config
      |    |    |- Docker.yaml
      |    |    |- Kubelet.yaml
      |    |    |- versions.yaml
      |    |
      |    |- /manifests
      |         |- bootstrap.yaml
      |         |- site.yaml
      |
      |- /networks
      |    |- /physical
      |    |    |- sitewide.yaml
      |    |    |- rack1.yaml
      |    |
      |    |- KubernetesNetwork.yaml
      |    |- common-addresses.yaml
      |
      |- /baremetal
           |- rack1.yaml
           |- rack2.yaml

  * Schemas - The schemas should all be sourced from the Airship
    service repositories. Care should be taken that the schemas
    included in the site definition are taken from the version of
    the service being deployed in the site.
  * Software
    * /config/versions.yaml will contain a manifest of all the
      chart, image and package versions. These should be substituted
      into all other documents that define version information.
    * dependencies.yaml - Contains Armada chart definitions that are
      only utilized as dependencies for other charts (e.g. helm-toolkit)
    * Chart collection - Loose organization of chart groups
      such as 'kubernetes', 'ucp', 'osh'
  * Physical networks and baremetal nodes can be split into files
    in whatever way makes sense. The best practice here to define
    them by racks is only a suggestion.

.. _Airship in a Bottle: https://opendev.org/airship/in-a-bottle

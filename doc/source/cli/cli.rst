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

.. _pegleg-cli:

==========
Pegleg CLI
==========

The Pegleg CLI is used in conjunction with the script located in pegleg/tools
called ``pegleg.sh``.

.. note::

  The default workspace for the ``pegleg.sh`` script is ``/workspace``. The
  examples below require that this workspace be used.

Environment Variables
=====================

::

    $WORKSPACE = Location of the folder that holds the repositories containing
    the site definition libraries. Pegleg makes no assumptions about the root
    directory. $WORKSPACE is /workspace in the container context.

        Example: $WORKSPACE=/home/ubuntu/all_repos

    $IMAGE = Location of pegleg docker image.

        Example: $IMAGE=quay.io/airshipit/pegleg:latest

Usage
=====

To run:

.. code-block:: console

    export WORKSPACE=<repo_location>
    export IMAGE=<docker_image>
    ./pegleg.sh <command> <options>

For example:

.. code-block:: console

  cd /opt/airship-pegleg
  export WORKSPACE=/opt/airship-treasuremap
  ./tools/pegleg.sh site -r /workspace --help

.. note::

  If ``sudo`` permissions are required to execute ``pegleg.sh``, then it is
  necessary to use the ``-E`` flag with ``sudo`` in order for the current
  environment to be used. For example:

  .. code-block:: console

    cd /opt/airship-pegleg
    export WORKSPACE=/opt/airship-treasuremap
    sudo -E ./tools/pegleg.sh site -r /workspace --help

CLI Options
===========

**-v / --verbose** (Optional). False by default.

Enable debug logging.

.. _site:

Repo
====

Allows you to perform repository-level operations.

Options
-------

**-r / --site-repository** (Required).

Path to the root of the site repository (containing site_definition.yaml) repo.

For example: /opt/aic-site-clcp-manifests.

The revision can also be specified via (for example):

::

  -r /opt/aic-site-clcp-manifests@revision

.. _cli-repo-lint:

Lint
----

Sanity checks for repository content (all sites in the repository). To lint
a specific site, see :ref:`site-level linting <cli-site-lint>`.

See :ref:`linting` for more information.

Site
====

Allows you to perform site-level operations.

::

  ./pegleg.sh site -r <site_repo> -e <extra_repo> <command> <options>

Options
-------

**-r / --site-repository** (Required).

Path to the root of the site repository (containing site_definition.yaml) repo.

For example: /opt/aic-site-clcp-manifests.

The revision can also be specified via (for example):

::

  -r /opt/aic-site-clcp-manifests@revision

**-e / --extra-repository** (Optional).

Path to the root of extra repositories used for overriding those specified
under the ``repositories`` field in a given :file:`site-definition.yaml`.

These should be named per the site-definition file, e.g.:

::

  -e global=/opt/global -e secrets=/opt/secrets

Repository Overrides
^^^^^^^^^^^^^^^^^^^^

By default, the revision specified in the :file:`site-definition.yaml` for the
site will be leveraged but can be
:ref:`overridden <command-line-repository-overrides>` using:

::

  -e global=/opt/global@revision

**-k / --repo-key** (Optional, SSH only).

The SSH public key to use when cloning remote authenticated repositories.

Required for cloning repositories via SSH protocol.

**-u / --repo-username** (Optional, SSH only).

The SSH username to use when cloning remote authenticated repositories
specified in the site-definition file. Any occurrences of ``REPO_USERNAME``
in an entry under the ``repositories`` field in a given
:file:`site-definition.yaml` will be replaced with this value.

Required for cloning repositories via SSH protocol.

Examples
^^^^^^^^

Example usage:

::

  ./pegleg.sh site -r /opt/aic-clcp-site-manifests/ \
    -u <AUTH_USER> \
    -k /opt/.ssh/gerrit.pub \
    -e global=ssh://REPO_USERNAME@<GERRIT URL>:29418/aic-clcp-manifests.git@master \
    <command> <options>

Collect
-------

Output complete config for one site.

**site_name** (Required).

Name of the site.

**-s / --save-location** (Optional).

Where to output collected documents. If omitted, the results will be dumped
to ``stdout``.

**-x <code>** (Optional, validation only).

Will exclude the specified lint option. -w takes priority over -x.

**-w <code>** (Optional, validation only).

Will warn of lint failures from the specified lint options.

**--validate** (Optional, validation only). False by default.

Perform validation of documents prior to collection. See :ref:`cli-site-lint`
for additional information on document linting. It is recommended that document
linting be executed prior to document collection. However, ``--validate``
is False by default for backwards compatibility concerns.

Usage:

::

    ./pegleg.sh <command> <options> collect <site_name> -s <save_location> \
      -x P001 -w P002 --validate

Examples
^^^^^^^^

Example without validation:

::

    ./pegleg.sh site -r /opt/aic-clcp-site-manifests \
      -e global=/opt/aic-clcp-manifests \
      collect <site_name> -s /workspace

Example with validation:

::

    ./pegleg.sh site -r /opt/aic-clcp-site-manifests \
      -e global=/opt/aic-clcp-manifests \
      collect <site_name> -s /workspace -x P004 --validate

List
----

List known sites.

**-o/--output** (Optional).

Where to output.

::

  ./pegleg <command> <options> list

Results are dumped to ``stdout`` by default.

Examples
^^^^^^^^

Example:

::

  ./pegleg site -r /opt/aic-clcp-site-manifests list -o /workspace

Show
----

Show details for one site.

**site_name** (Required).

Name of site.

**-o /--output** (Optional).

Where to output.

::

  ./pegleg <command> <options> show site_name

Results are dumped to ``stdout`` by default.

Examples
^^^^^^^^

Example:

::

  ./pegleg site -r /opt/aic-clcp-site-manifests show site_name -o /workspace

Render
------

Render documents via `Deckhand`_ for one site.

**site_name** (Required).

Name of site.

**-o /--output** (Optional).

Where to output.

::

  ./pegleg <command> <options> render site_name

Results are dumped to ``stdout`` by default.

Examples
^^^^^^^^

Example:

::

  ./pegleg site -r /opt/aic-clcp-site-manifests render site_name -o output

.. _cli-site-lint:

Lint
----

Sanity checks for repository content (for a specific site in the repository).
Validations for linting are done utilizing `Deckhand Validations`_.

To lint all sites in the repository, see
:ref:`repository-level linting <cli-repo-lint>`.

See :ref:`linting` for more information.

Examples
^^^^^^^^

Generic example:

::

  ./pegleg.sh site -r <site_repo> -e <extra_repo> \
    lint <site_name> \
    -f -x <lint_code> -w <lint_code>

The most basic way to lint a document set is as follows:

::

  ./pegleg.sh site -r <site_repo> -e <extra_repo> lint <site_name>

A more complex example involves excluding certain linting checks:

::

  ./pegleg.sh site -r /opt/aic-clcp-site-manifests \
    -e global=/opt/aic-clcp-manifests \
    lint <site_name> \
    -x P001 -x P002 -w P003

.. _command-line-repository-overrides:

CLI Repository Overrides
------------------------

Repository overrides should only be used for entries included underneath
the ``repositories`` field for a given :file:`site-definition.yaml`.

Overrides are specified via the ``-e`` flag for all :ref:`site` commands. They
have the following format:

::

  -e <REPO_NAME>=<REPO_PATH_OR_URL>@<REVISION>

Where:

  * REPO_NAME is one of: ``global``, ``secrets`` or ``site``.
  * REPO_PATH_OR_URL is one of:

    * path (relative or absolute) - /opt/global or ../global though absolute is
      recommended
    * url (fully qualified) - must have following formats:

      * ssh - <PROTOCOL>://<REPO_USERNAME>@<GERRIT URL>:<PORT>/<REPO_NAME>.git
      * http|https - <PROTOCOL>://<GERRIT URL>/<REPO_NAME>.git

    Where:

      * <PROTOCOL> must be a valid authentication protocol: ssh, https, or http
      * <REPO_USERNAME> must be a user with access rights to the repository.
        This value will replace the literal string REPO_USERNAME in the
        corresponding entry under the ``repositories`` field in the relevant
        :file:`site-definition.yaml` using ``-u`` CLI flag
      * <GERRIT_URL> must be a valid Gerrit URL
      * <PORT> must be a valid authentication port for SSH
      * <REVISION> must be a valid :ref:`git-reference`
      * <REPO_NAME> must be a valid Git repository name,
        e.g. aic-clcp-site-manifests

.. _self-contained-repo:

Self-Contained Repository
^^^^^^^^^^^^^^^^^^^^^^^^^

For self-contained repositories, specification of extra repositories is
unnecessary. The following command can be used to deploy the manifests in
the example repository ``/opt/airship-in-a-bottle`` for the *currently checked
out revision*:

::

  pegleg site -r /opt/airship-in-a-bottle/deployment_files <command> <options>

To specify a specific revision at run time, execute:

::

  pegleg site -r /opt/airship-in-a-bottle/deployment_files@<REVISION> \
    <command> <options>

Where ``<REVISION>`` must be a valid :ref:`git-reference`.

.. _git-reference:

Git Reference
^^^^^^^^^^^^^

Valid Git references for checking out repositories include:

  * 47676764d3935e4934624bf9593e9115984fe668 (commit ID)
  * refs/changes/79/47079/12 (ref)
  * master (branch name)

.. _linting:

Linting
=======

**-f / --fail-on-missing-sub-src** (Optional).

Raise Deckhand exception on missing substitution sources. Defaults to True.

**-x <code>** (Optional).

Will exclude the specified lint option. -w takes priority over -x.

**-w <code>** (Optional).

Will warn of lint failures from the specified lint options.

If you expect certain lint failures, then those lint options can be
excluded or you can choose to be warned about those failures using the
codes below.

P001 - Document has storagePolicy cleartext (expected is encrypted) yet
its schema is a mandatory encrypted type.

Where mandatory encrypted schema type is one of:

* deckhand/CertificateAuthorityKey/v1
* deckhand/CertificateKey/v1
* deckhand/Passphrase/v1
* deckhand/PrivateKey/v1

P002 - Deckhand rendering is expected to complete without errors.
P003 - All repos contain expected directories.

.. _Deckhand: https://airship-deckhand.readthedocs.io/en/latest/rendering.html
.. _Deckhand Validations: https://airship-deckhand.readthedocs.io/en/latest/validation.html

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

        Example: $IMAGE=quay.io/airshipit/pegleg:latest-ubuntu_xenial

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

**-v / --verbose** (Optional, Default=False).

Enable debug logging.

.. _repo-group:

Repo Group
==========

Allows you to perform repository-level operations.

Options
-------

**-r / --site-repository** (Required).

Path to the root of the site repository (containing site_definition.yaml) repo.

For example: /opt/airship-treasuremap

The revision can also be specified via (for example):

::

  -r /opt/airship-treasuremap@revision

**-p / --clone-path** (Optional, Default=/tmp/).

The path where the repo will be cloned. If this option is included and the
repo already exists, then the repo will not be cloned again and the user must
specify a new clone path or pass in the local copy of the repository as the
site repository. Suppose the repo name is airship-treasuremap and the clone
path is /tmp/mypath then the following directory is created
/tmp/mypath/airship-treasuremap which will contain the contents of the repo.
Example of using clone path:

::

  -p /tmp/mypath

.. _cli-repo-lint:

Lint
----

Sanity checks for repository content (all sites in the repository). To lint
a specific site, see :ref:`site-level linting <cli-site-lint>`.

See :ref:`linting` for more information.

.. _site-group:

Site Group
==========

Allows you to perform site-level operations.

::

  ./pegleg.sh site -r <site_repo> -e <extra_repo> <command> <options>

Options
-------

**-r / --site-repository** (Required).

Path to the root of the site repository (containing site_definition.yaml) repo.

For example: /opt/airship-treasuremap

The revision can also be specified via (for example):

::

  -r /opt/airship-treasuremap@revision

**-e / --extra-repository** (Optional).

Path to the root of extra repositories used for overriding those specified
under the ``repositories`` field in a given :file:`site-definition.yaml`.

These should be named per the site-definition file, e.g.:

::

  -e global=/opt/global -e secrets=/opt/secrets

**-p / --clone-path** (Optional, Default=/tmp/).

The path where the repo will be cloned. If this option is included and the
repo already exists, then the repo will not be cloned again and the user must
specify a new clone path or pass in the local copy of the repository as the
site repository. Suppose the repo name is airship-treasuremap and the clone
path is /tmp/mypath then the following directory is created
/tmp/mypath/airship-treasuremap which will contain the contents of the repo.
Example of using clone path:

::

  -p /tmp/mypath

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

**-u / --repo-username** (Optional, unless required by repo URL).

The SSH username to use when cloning remote authenticated repositories
specified in the site-definition file. Any occurrences of ``REPO_USERNAME``
in an entry under the ``repositories`` field in a given
:file:`site-definition.yaml` will be replaced with this value.

Required for cloning repositories via SSH protocol.
This argument will generate an exception if no repo URL
uses ``REPO_USERNAME``.

Examples
^^^^^^^^

Example usage:

::

  ./pegleg.sh site -r /opt/site-manifests/ \
    -u <AUTH_USER> \
    -k /opt/.ssh/git.pub \
    -e global=ssh://REPO_USERNAME@<GIT URL>:29418/global-manifests.git@master \
    <command> <options>

Collect
-------

Output complete config for one site.

**site_name** (Required).

Name of the site.

**-s / --save-location** (Optional).

Where to output collected documents. If omitted, the results will be dumped
to ``stdout``.

**-x** (Optional, validation only).

Will exclude the specified lint option. -w takes priority over -x.

**-w** (Optional, validation only).

Will warn of lint failures from the specified lint options.

**--validate** (Optional, validation only, Default=False).

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

    ./pegleg.sh site -r /opt/site-manifests \
      -e global=/opt/manifests \
      collect <site_name> -s /workspace

Example with validation:

::

    ./pegleg.sh site -r /opt/site-manifests \
      -e global=/opt/manifests \
      collect <site_name> -s /workspace -x P004 --validate

List
----

List known sites.

**-o / --output** (Optional, Default=stdout).

Where to output.

::

  ./pegleg <command> <options> list

Examples
^^^^^^^^

Example:

::

  ./pegleg site -r /opt/site-manifests list -o /workspace

Show
----

Show details for one site.

**site_name** (Required).

Name of site.

**-o / --output** (Optional, Default=stdout).

Where to output.

::

  ./pegleg <command> <options> show site_name

Examples
^^^^^^^^

Example:

::

  ./pegleg site -r /opt/site-manifests show site_name -o /workspace

Render
------

Render documents via `Deckhand`_ for one site.

**site_name** (Required).

Name of site.

**-o / --output** (Optional, Default=stdout).

Where to output.

**-v / --validate** (Optional, Default=True).

Whether to pre-validate documents using built-in schema validation.
Skips over externally registered DataSchema documents to avoid
false positives.

::

  ./pegleg <command> <options> render site_name

Examples
^^^^^^^^

Example:

::

  ./pegleg site -r /opt/site-manifests render site_name -o output

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

  ./pegleg.sh site -r /opt/site-manifests \
    -e global=/opt/manifests \
    lint <site_name> \
    -x P001 -x P002 -w P003

Upload
-------

Uploads documents to `Shipyard`_.

**site_name** (Required).

Name of the site. The ``site_name`` must match a ``site`` name in the site
repository folder structure

**--os-<various>** (Required).

Shipyard needs these options for authenticating with OpenStack Keystone.
This option can be set as environment variables or it can be passed via
the command line.

Please reference Shipyard's `CLI documentation`_ for information related to these options.

**--context-marker** (Optional).

Specifies a UUID (8-4-4-4-12 format) that will be used to correlate logs,
transactions, etc. in downstream activities triggered by this interaction.

**-b / --buffer-mode** (Optional, Default=auto).

Set the buffer mode when uploading documents. Supported buffer modes
include append, replace, auto.

append: Add the collection to the Shipyard Buffer, only if that
collection does not already exist in the Shipyard buffer.

replace: Clear the Shipyard Buffer before adding the specified
collection.

**--collection** (Required, Default=<site_name>).

Specifies the name of the compiled collection of documents that will be
uploaded to Shipyard.

Usage:

::

    ./pegleg.sh site <options> upload <site_name> --context-marker=<uuid> \
                                                  --buffer-mode=<buffer> \
                                                  --collection=<collection>

Site Secrets Group
------------------

Subgroup of :ref:`site-group`.

A sub-group of site command group, which allows you to perform secrets
level operations for secrets documents of a site.

.. note::

  For the CLI commands ``encrypt``, ``decrypt``, ``generate-pki``, and ``wrap``
  in the ``secrets`` command
  group, which encrypt or decrypt site secrets, two  environment variables,
  ``PEGLEG_PASSPHRASE``, and ``PEGLEG_SALT``, are  used to capture the
  master passphrase, and the salt needed for encryption and decryption of the
  site secrets. The contents of ``PEGLEG_PASSPHRASE``, and ``PEGLEG_SALT``
  are not generated by Pegleg, but are created externally, and set by
  deployment engineers or tooling.

  A minimum length of 24 for master passphrases will be checked by all CLI
  commands, which use the ``PEGLEG_PASSPHRASE`` and ``PEGLEG_SALT``.
  All other criteria around master passphrase strength are assumed to be
  enforced elsewhere.

::

  ./pegleg.sh site -r <site_repo> -e <extra_repo> secrets <command> <options>


Generate PKI
^^^^^^^^^^^^

Generate certificates and keys according to all PKICatalog documents in the
site using the PKI module. The default behavior is to generate all
certificates that are not yet present. For example, the first time generate PKI
is run or when new entries are added to the PKICatalogue, only those new
entries will be generated on subsequent runs.

Pegleg also supports a full regeneration of all certificates at any time, by
using the --regenerate-all flag.

Pegleg places generated document files in ``<site>/secrets/passphrases``,
``<site>/secrets/certificates``, or ``<site>/secrets/keypairs`` as
appropriate:

* The generated filenames for passphrases will follow the pattern
  :file:`<passphrase-doc-name>.yaml`.
* The generated filenames for certificate authorities will follow the pattern
  :file:`<ca-name>_ca.yaml`.
* The generated filenames for certificates will follow the pattern
  :file:`<ca-name>_<certificate-doc-name>_certificate.yaml`.
* The generated filenames for certificate keys will follow the pattern
  :file:`<ca-name>_<certificate-doc-name>_key.yaml`.
* The generated filenames for keypairs will follow the pattern
  :file:`<keypair-doc-name>.yaml`.

Dashes in the document names will be converted to underscores for consistency.

**site_name** (Required).

Name of site.

**-a / --author** (Optional).

Identifying name of the author generating new certificates. Used for tracking
provenance information in the PeglegManagedDocuments. An attempt is made to
automatically determine this value, but should be provided.

**-d / --days** (Optional, Default=365).

Duration (in days) certificates should be valid.
Minimum=0, no maximum.  Values less than 0 will raise an exception.

NOTE: A generated certificate where days = 0 should only be used for testing.
A certificate generated in such a way will be valid for 0 seconds.

**--regenerate-all** (Optional, Default=False).

Force Pegleg to regenerate all PKI items.

Examples
""""""""

::

  ./pegleg.sh site -r <site_repo> -e <extra_repo> \
    secrets generate-pki \
    <site_name> \
    -a <author> \
    -d <days> \
    --regenerate-all

.. _command-line-repository-overrides:


Check PKI Certs
---------------

Determine if any PKI certificates from a site are expired, or will be expired
within ``days`` days.  If any are found, print the cert names and expiration
dates to ``stdout``.

**-d / --days** (Optional, Default=60).

Duration (in days) to check certificate validity from today.
Minimum=0, no maximum.  Values less than 0 will raise an exception.

NOTE: Checking PKI certs where days = 0 will check for certs that are expired
at the time the command is run.

**site_name** (Required).

Name of the ``site``. The ``site_name`` must match a ``site`` name in the site
repository folder structure.

Usage:

::

    ./pegleg.sh site -r <site_repo> \
      secrets check-pki-certs <site_name> <options>

Examples
^^^^^^^^

Example without days specified:

::

    ./pegleg.sh site -r <site_repo> secrets check-pki-certs <site_name>

Example with days specified:

::

    ./pegleg.sh site -r <site_repo> secrets check-pki-certs <site_name> -d <days>

Secrets
-------

A sub-group of site command group, which allows you to perform secrets
level operations for secrets documents of a site.

.. note::

  For the CLI commands ``encrypt`` and ``decrypt`` in the ``secrets`` command
  group, which encrypt or decrypt site secrets, two  environment variables,
  ``PEGLEG_PASSPHRASE``, and ``PEGLEG_SALT``, are  used to capture the
  master passphrase, and the salt needed for encryption and decryption of the
  site secrets. The contents of ``PEGLEG_PASSPHRASE``, and ``PEGLEG_SALT``
  are not generated by Pegleg, but are created externally, and set by a
  deployment engineers or tooling.

  A minimum length of 24 for master passphrases will be checked by all CLI
  commands, which use the ``PEGLEG_PASSPHRASE``. All other criteria around
  master passphrase strength are assumed to be enforced elsewhere.

::

  ./pegleg.sh site -r <site_repo> -e <extra_repo> secrets <command> <options>



Encrypt
^^^^^^^

Encrypt one site's secrets documents, which have the
``metadata.storagePolicy`` set to encrypted, and wrap them in
`Pegleg Managed Documents`_

.. note::

  The encrypt command is idempotent. If the command is executed more
  than once for a given site, it will skip the files, which are already
  encrypted and wrapped in a pegleg managed document, and will only encrypt the
  documents not encrypted before.

**site_name** (Required).

Name of the ``site``. The ``site_name`` must match a ``site`` name in the site
repository folder structure. The ``encrypt`` command looks up the
``site-name`` in the site repository, and searches recursively the
``site_name`` folder structure for secrets files (i.e. files with documents,
whose ``encryptionPolicy`` is set to ``encrypted``), and encrypts the
documents in those files.

**-a / --author** (Required)

Author is the identifier for the program or the person, who is encrypting
the secrets documents.
Author is intended to document the entity or the individual, who
encrypts the site secrets documents, mostly for tracking purposes, and is
expected to be leveraged in an operator-specific manner.
For instance the ``author`` can be the "userid" of the person running the
command, or the "application-id" of the application executing the command.

**-s / --save-location** (Optional).

Where to output the encrypted and wrapped documents.

.. warning::

  If the ``save-location`` parameter is not provided, the encrypted result
  documents will overwrite the original ``cleartext`` documents for the site.
  The reason for this default behavior, is to ensure that site secrets are
  only stored on disk or in any version control system as encrypted.

  If the user for any reason wants to avoid overwriting the original
  cleartext files, the ``save-location`` parameter will provide the option to
  override this default behavior, and forces the encrypt command to write
  the encrypted documents in a different location than the original
  unencrypted files.


Usage:

::

    ./pegleg.sh site <options> secrets encrypt <site_name> -a <author_id> -s <save_location>

Examples
""""""""

Example with optional save location:

::

    ./pegleg.sh site -r /opt/site-manifests \
      -e global=/opt/manifests \
      -e secrets=/opt/security-manifests \
      secrets encrypt <site_name> -a <author_id> -s /workspace

Example without optional save location:

::

    ./pegleg.sh site -r /opt/site-manifests \
      -e global=/opt/manifests \
      -e secrets=/opt/security-manifests \
      secrets encrypt <site_name> -a <author_id>

Decrypt
^^^^^^^

Unwrap one or more encrypted secrets document from
`Pegleg Managed Documents`_, decrypt the encrypted secrets, and dump the
cleartext to stdout or a specified location.

**site_name** (Required).

Name of the ``site``. The ``site_name`` must match a ``site`` name in the site
repository folder structure. This is used to ensure the correct revision of
the site and global repositories are used, as specified in the site's
:file:`site-definition.yaml`.

**--path** (Required).

Path to pegleg managed encrypted secrets file or directory of files.

**-s / --save-location** (Optional).

The desired output path for the decrypted file. If not specified, decrypted
data will output to stdout.

**-o / --overwrite** (Optional). False by default.

When set, encrypted file(s) at the specified path will be overwritten with
the decrypted data. Overrides ``--save-location`` option.

Usage:

::

    ./pegleg.sh site <options> secrets decrypt <site_name> --path <path>
      [-s <output_path>]

Examples
""""""""

Example:

::

    ./pegleg.sh site -r /opt/site-manifests \
      -e global=/opt/manifests \
      -e secrets=/opt/security-manifests \
      secrets decrypt site1 -f \
      /opt/security-manifests/site/site1/passwords/password1.yaml

Wrap
^^^^

Wrap bare files (e.g. pem or crt) in a PeglegManagedDocument and optionally encrypt them.

**site_name** (Required).

Name of site.

**-a / --author**

Identifying name of the author generating new certificates. Used
for tracking provenance information in the PeglegManagedDocuments.
An attempt is made to automatically determine this value,
but should be provided.

**--filename**

The relative path to the file to be wrapped.

**-o / --output-path**

The output path for the wrapped file. (default: input path with the extension
replaced with .yaml)

**-s / --schema**

The schema for the document to be wrapped, e.g. deckhand/Certificate/v1

**-n / --name**

The name for the document to be wrapped, e.g. new-cert.

**-l / --layer**

The layer for the document to be wrapped, e.g. site.

**--encrypt / --no-encrypt** (Default=True).

A flag specifying whether to encrypt the output file.

Examples
""""""""

::

  ./pegleg.sh site -r /home/myuser/myrepo \
    secrets wrap -a myuser --filename secrets/certificates/new_cert.crt \
    -o secrets/certificates/new_cert.yaml -s "deckhand/Certificate/v1" \
    -n "new-cert" -l site mysite


genesis_bundle
--------------

Constructs genesis bundle based on a site configuration.

.. note::
  This command requires the environment variable PEGLEG_PASSPHRASE
  to be set and at least 24 characters long, to be used for encrypting
  genesis bundle data. PEGLEG_SALT must be set as well. There are no
  constraints on its length, but at least 24 characters is recommended.


**-b / --build-dir** (Required).

Destination directory for the genesis bundle.

**--include-validators** (Optional, Default=False).

A flag to request build genesis validation scripts as well.

Usage:

::
    ./pegleg.sh site <options> genesis_bundle <site_name> \
      -b <build_locaton> -k <encryption_passphrase/key> --include-validators

Examples
^^^^^^^^

::

    ./pegleg.sh site -r  ./site-manifests \
      genesis_bundle site1 \
      -b ../../site1_build \
      -k yourEncryptionPassphrase \
      --include-validators

generate
^^^^^^^^
A sub-group of secrets command group, which allows you to auto-generate
secrets documents of a site.

.. note::

  The types of documents that pegleg cli generates are
  passphrases, certificate authorities, certificates and keys. Passphrases are
  declared in a new ``pegleg/PassphraseCatalog/v1`` document, while CAs,
  certificates, and keys are declared in the ``pegleg/PKICatalog/v1``.

  The ``pegleg/PKICatalog/v1`` schema is identical with the existing
  ``promenade/PKICatalog/v1``, promenade currently uses to generate the site
  CAs, certificates, and keys.

  The ``pegleg/PassphraseCatalog/v1`` schema is specified in
  `Pegleg Passphrase Catalog`_

::

./pegleg.sh site -r <site_repo> -e <extra_repo> secrets generate <command> <options>

passphrases
"""""""""""
Generates, wraps and encrypts passphrase documents specified in the
``pegleg/PassphraseCatalog/v1`` document for a site. The site name, and the
directory to store the generated documents are provided by the
``site_name``, and the ``save_location`` command line parameters respectively.
The generated passphrases are stored in:

::

<save_location>/site/<site_name>/passphrases/<passphrase_name.yaml>

The schema for the generated passphrases is defined in
`Pegleg Managed Documents`_

**site_name** (Required).

Name of the ``site``. The ``site_name`` must match a ``site`` name in the site
repository folder structure. The ``generate`` command looks up the
``site-name``, and searches recursively the ``site_name`` folder structure
in the site repository for ``pegleg/PassphraseCatalog/v1`` documents. Then it
parses the passphrase catalog documents it found, and generates one passphrase
document for each passphrase ``document_name`` declared in the site passphrase
catalog.

**-a / --author** (Required)


``Author`` is intended to document the application or the individual, who
generates the site passphrase documents, mostly for tracking purposes. It
is expected to be leveraged in an operator-specific manner.
For instance the ``author`` can be the "userid" of the person running the
command, or the "application-id" of the application executing the command.

**-s / --save-location** (Required).

Where to output generated passphrase documents. The passphrase documents
are placed in the following folder structure under ``save_location``:

::

<save_location>/site/<site_name>/secrets/passphrases/<passphrase_name.yaml>

**-i / --interactive** (Optional). False by default.

Generate passphrases interactively, not automatically.

**--force-cleartext** (Optional). False by default.

Force cleartext generation of passphrases. This is not
recommended.

Usage:

::

    ./pegleg.sh site <options> secrets generate passphrases <site_name> -a
    <author_id> -s <save_location>

Example
""""""""

::

    ./pegleg.sh site -r /opt/site-manifests \
      -e global=/opt/manifests \
      -e secrets=/opt/security-manifests \
      secrets generate passphrases <site_name> -a <author_id> -s /workspace


CLI Repository Overrides
========================

Repository overrides should only be used for entries included underneath
the ``repositories`` field for a given :file:`site-definition.yaml`.

Overrides are specified via the ``-e`` flag for all :ref:`site-group` commands.
They have the following format:

::

  -e <REPO_NAME>=<REPO_PATH_OR_URL>@<REVISION>

Where:

  * REPO_NAME is one of: ``global``, ``secrets`` or ``site``.
  * REPO_PATH_OR_URL is one of:

    * path (relative or absolute) - /opt/global or ../global though absolute is
      recommended
    * url (fully qualified) - must have following formats:

      * ssh - <PROTOCOL>://<REPO_USERNAME>@<GIT URL>:<PORT>/<REPO_NAME>.git
      * http|https - <PROTOCOL>://<GIT URL>/<REPO_NAME>.git

    Where:

      * <PROTOCOL> must be a valid authentication protocol: ssh, https, or http
      * <REPO_USERNAME> must be a user with access rights to the repository.
        This value will replace the literal string REPO_USERNAME in the
        corresponding entry under the ``repositories`` field in the relevant
        :file:`site-definition.yaml` using ``-u`` CLI flag
      * <GIT_URL> must be a valid Git URL
      * <PORT> must be a valid authentication port for SSH
      * <REVISION> must be a valid :ref:`git-reference`
      * <REPO_NAME> must be a valid Git repository name,
        e.g. site-manifests

.. _self-contained-repo:

Self-Contained Repository
-------------------------

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

**-f / --fail-on-missing-sub-src** (Optional, Default=True).

Raise Deckhand exception on missing substitution sources.

**-x** (Optional).

Will exclude the specified lint option. -w takes priority over -x.

**-w** (Optional).

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


.. _Deckhand: https://airship-deckhand.readthedocs.io/en/latest/users/rendering.html
.. _Deckhand Validations: https://airship-deckhand.readthedocs.io/en/latest/overview.html#validation
.. _Pegleg Managed Documents: https://airship-specs.readthedocs.io/en/latest/specs/approved/pegleg-secrets.html#peglegmanageddocument
.. _Shipyard: https://opendev.org/airship/shipyard
.. _CLI documentation: https://airship-shipyard.readthedocs.io/en/latest/CLI.html#openstack-keystone-authorization-environment-variables
.. _Pegleg Passphrase Catalog: https://airship-specs.readthedocs.io/en/latest/specs/approved/pegleg-secrets.html#document-generation


Generate
========

Allows you to perform generate operations.

Passphrase
----------

Generate a passphrase and print to ``stdout``.

**-l / --length** (Optional, Default=24).

Length of passphrase to generate.
Minimum length is 24. Lengths less than minimum will default to 24.
No maximum length.

Usage:

::

    ./pegleg.sh generate passphrase -l <length>

Examples
^^^^^^^^

Example without length specified:

::

    ./pegleg.sh generate passphrase

Example with length specified:

::

    ./pegleg.sh generate passphrase -l <length>

Salt
----

Generate a salt and print to ``stdout``.

**-l / --length** (Optional, Default=24).

Length of salt to generate.
Minimum length is 24. Lengths less than minimum will default to 24.
No maximum length.

Usage:

::

    ./pegleg.sh generate salt -l <length>

Examples
^^^^^^^^

Example without length specified:

::

    ./pegleg.sh generate salt

Example with length specified:

::

    ./pegleg.sh generate salt -l <length>

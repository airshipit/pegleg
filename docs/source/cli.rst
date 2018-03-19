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

==========
Pegleg CLI
==========

The Pegleg CLI is used in conjunction with the script located in pegleg/tools
called pegleg.sh.

::

    $WORKSPACE = Location of the folder that holds the repositories containing
    the site definition libraries. Pegleg makes no assumptions about the root
    directory. $WORKSPACE is /workspace in the container context.

    $IMAGE = Location of pegleg docker image.

To run:

./pegleg.sh <command> <options>


CLI Options
===========

**-v / --verbose**

Enable debug logging.

Site
----
Commands related to sites.

**-p / --primary**

Path to the root of the primary (containing site_definition.yaml) repo.
(Required).

**-a / --auxiliary**

Path to the root of an auxiliary repo.

::

    ./pegleg.sh site -p <primary_repo> -a <auxiliary_repo> <command> <options>

    Example:
    ./pegleg.sh site -p /workspace/repo_1 -a /workspace/repo_2
    <command> <options>

Collect
-------
Output complete config for one site. It is assumed that all lint errors have
been corrected already.

**site_name**

Name of the site. (Required).

**-s / --save-location**

Where to output.

::

    ./pegleg.sh <command> <options> collect site_name -s save_location

    Example:
    ./pegleg.sh site -p /workspace/repo_1 -a /workspace/repo_2
    collect site_name -s /workspace

Impacted
--------
Find sites impacted by changed files.

**-i / --input**

List of impacted files.

**-o / --output**

Where to output.

::

    ./pegleg impacted -i <input_stream> -o <output_stream>

List
----
List known sites.

**-o/--output**

Where to output.

::

    ./pegleg <command> <options> list

    Example:
    ./pegleg site -p /workspace/repo_1 list -o /workspace

Show
----
Show details for one site.

**site_name**

Name of site. (Required).

**-o /--output**

Where to output.

::

    ./pegleg <command> <options> show site_name

    Example:
    ./pegleg site -p /workspace/repo_1 show site_name -o /workspace



Lint
----
Sanity checks for repository content.

::

    ./pegleg.sh lint -p <primary_repo> -a <auxiliary_repo>
    -f -x <lint_code> -w <lint_code>

    Example:

    ./pegleg.sh lint -p /workspace/site-repo -a /workspace/secondary-repo
    -x P001 -x P002 -w P003

**-p / --primary**

Path to the root of the primary (containing site_definition.yaml) repo.
(Required).

**-a / --auxiliary**

Path to the root of an auxiliary repo.

**-f / --fail-on-missing-sub-src**

Raise Deckhand exception on missing substitution sources. Defaults to True.

**-x <code>**

Will excluded the specified lint option. -w takes priority over -x.

**-w <code>**

Will warn of lint failures from the specified lint options.

::

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

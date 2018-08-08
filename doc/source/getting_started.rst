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

===============
Getting Started
===============

What is Pegleg?
---------------

Pegleg is a document aggregator that will aggregate all the documents in a
repository and pack them into a single YAML file. This allows for operators to
structure their site definitions in a maintainable directory layout, while
providing them with the automation and tooling needed to aggregate, lint, and
render those documents for deployment.

For more information on the documents that Pegleg works on see `Document Fundamentals`_.

Basic Usage
-----------

Before using Pegleg, you must:

1. Clone the Pegleg repository:

.. code-block:: console

    git clone https://git.airshipit.org/airship-pegleg

2. Install the required packages in airship-pegleg/src/bin/pegleg:

.. code-block:: console

     pip3 install -r airship-pegleg/src/bin/pegleg/requirements.txt -r airship-pegleg/src/bin/pegleg/test-requirements.txt

3. Clone the repos containing your `site definition libraries`_ into the
local filesystem where Pegleg is running, as Pegleg can only work with files
available in the local directory.

You will then be able to use all of Pegleg's features through the CLI. See CLI_ for more
information.

.. _Document Fundamentals: https://airship-pegleg.readthedocs.io/en/latest/authoring_strategy.html
.. _CLI: https://airship-pegleg.readthedocs.io/en/latest/cli.html
.. _Deckhand: https://airship-deckhand.readthedocs.io/en/latest/
.. _site definition libraries: https://airship-pegleg.readthedocs.io/en/latest/artifacts.html#definition-library-layout

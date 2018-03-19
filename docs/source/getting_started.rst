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

Pegleg is document aggregator that provides early linting and validations for
documents that can be consumed by UCP.

For more information on the documents that Pegleg works on see `Document Fundamentals`_.

Basic Usage
-----------

Before using Pegleg, you must install the required packages in pegleg/src/bin/pegleg

.. code-block:: console

     pip3 install -r pegleg/src/bin/pegleg/requirements.txt -r pegleg/src/bin/pegleg/test-requirements.txt


You will then be able to use all of Pegleg's features through the CLI. See CLI_ for more
information.

.. _Document Fundamentals: https://pegleg.readthedocs.io/en/latest/authoring_strategy.html
.. _CLI: https://pegleg.readthedocs.io/en/latest/cli.html

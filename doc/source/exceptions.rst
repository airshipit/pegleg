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

Pegleg  Exceptions
==================

.. currentmodule:: pegleg.engine.exceptions

Base Exceptions
---------------

.. autoexception:: PeglegBaseException
   :members:
   :undoc-members:

Git Exceptions
--------------

.. autoexception:: GitConfigException
   :members:
   :show-inheritance:
   :undoc-members:

.. autoexception:: GitException
   :members:
   :show-inheritance:
   :undoc-members:

.. autoexception:: GitAuthException
   :members:
   :show-inheritance:
   :undoc-members:

.. autoexception:: GitProxyException
   :members:
   :show-inheritance:
   :undoc-members:

.. autoexception:: GitSSHException
   :members:
   :show-inheritance:
   :undoc-members:

.. autoexception:: GitInvalidRepoException
   :members:
   :show-inheritance:
   :undoc-members:

Authentication Exceptions
-------------------------

.. autoexception:: pegleg.engine.util.shipyard_helper.AuthValuesError
   :members:
   :undoc-members:

PKI Exceptions
--------------

.. autoexception:: IncompletePKIPairError

Genesis Bundle Exceptions
-------------------------

.. autoexception:: GenesisBundleEncryptionException
   :members:
   :show-inheritance:
   :undoc-members:

.. autoexception:: GenesisBundleGenerateException
   :members:
   :show-inheritance:

Passphrase Exceptions
---------------------

.. autoexception:: PassphraseCatalogNotFoundException
   :members:
   :show-inheritance:
   :undoc-members:

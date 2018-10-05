======
Pegleg
======

|Docker Repository on Quay| |Doc Status|

Introduction
============

Pegleg is a document aggregator that provides early linting and validations via
`Deckhand`_, a document management micro-service within `Airship`_.

Pegleg supports local and remote `Git`_ repositories. Remote repositories
can be cloned using a variety of protocols -- HTTP(S) or SSH. Afterward,
specific revisions within those repositories can be checked out, their
documents aggregated, linted, and passed to the rest of `Airship`_ for
orchestration, allowing document authors to manage their site definitions using
version control.

Find more documentation for Pegleg on `Read the Docs`_.

Core Responsibilities
=====================

* aggregation - Aggregates all documents required for site deployment across
  multiple `Git`_ repositories, each of which can be used to maintain separate
  document sets in isolation
* linting - Configurable linting checks documents for common syntactical and
  semantical mistakes

Getting Started
===============

For more detailed installation and setup information, please refer to the
`Getting Started`_ guide.

Integration Points
==================

Pegleg has the following integration points:

  * `Deckhand`_ which provides document revision management, storage and
    rendering functionality upon which the rest of the `Airship`_ components
    rely for orchestration of infrastructure provisioning.

Further Reading
===============

`Airship`_.

.. |Docker Repository on Quay| image:: https://quay.io/repository/airshipit/pegleg/status
   :target: https://quay.io/repository/airshipit/pegleg
.. |Doc Status| image:: https://readthedocs.org/projects/airship-pegleg/badge/?version=latest
   :target: https://airship-pegleg.readthedocs.io/
.. _Deckhand: https://airship-deckhand.readthedocs.io
.. _Airship: https://www.airshipit.org
.. _Read the Docs:  https://airship-pegleg.readthedocs.io
.. _Getting Started: https://airship-pegleg.readthedocs.io/en/latest/getting-started.html
.. _Git: https://git-scm.com/

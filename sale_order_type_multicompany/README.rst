.. |company| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

============================
Sale Order Type Multicompany
============================

This module extends the Sale Order Type functionality to support multicompany environments with parent-child company relationships.

Features
--------

* Allows sale order types to use journals from parent companies in child companies
* Respects the "shared_to_branches" configuration from account_ux module
* Adapts check_company constraints for fiscal positions and teams to work with parent-child company hierarchies

Configuration
=============

No additional configuration is required beyond installing the module.

Usage
=====

Once installed, sale order types in child companies can use journals that are marked as "shared_to_branches" in their parent companies.

Known issues / Roadmap
======================

* None

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/ingadhoc/multi-company/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.

Credits
=======

Images
------

* ADHOC SA: `Icon <http://adhoc.com.ar>`_.

Contributors
------------

Maintainer
----------

.. image:: http://adhoc.com.ar/logo.png
   :alt: Adhoc SA
   :target: http://adhoc.com.ar

This module is maintained by the ADHOC SA.

To contribute to this module, please visit https://www.adhoc.com.ar.

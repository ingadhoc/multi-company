.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

==============================
Account Multicompany Usability
==============================

#. Allow to work with properties of all companies without needing to change between companies (rendered as a many2many)
#. You can also set companies as consolidation companies, for this companies creation of accounting entries is forbiden
#. Add new field short_name on company that is used later to be appended on the "display name" of the journals. This is usefull because when you select journals you don't have a filter of the companies. (TODO check if we can avoid all this and have a different approach)

Installation
============

To install this module, you need to:

#. Only install the module

Configuration
=============

To configure this module, you need to:

#. Nothing to configure

Usage
=====

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: http://runbot.adhoc.com.ar/

Bug Tracker
===========

Bugs are tracked on `GitHub Issues
<https://github.com/ingadhoc/multi-company/issues>`_. In case of trouble, please
check there if your issue has already been reported. If you spotted it first,
help us smashing it by providing a detailed and welcomed feedback.

Credits
=======

.. |iconEficent| image:: https://avatars0.githubusercontent.com/u/7718403?s=200&v=4
    :width: 13px
    :height: 13px
    :alt: Eficent

* |company| |icon|
* Eficent |iconEficent| Part of the code used for this module was extracted from Eficent's `multicompany-fixes/mcfix_accpount <https://github.com/Eficent/multicompany-fixes/tree/11.0/mcfix_account>`_ module

Contributors
------------

Maintainer
----------

|company_logo|

This module is maintained by the |company|.

To contribute to this module, please visit https://www.adhoc.com.ar.

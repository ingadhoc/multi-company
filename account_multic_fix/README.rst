.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

===========================
Account Multi Company Fixes
===========================

#. Add check_company on account.move and account.move.line (backported from odoo master https://github.com/odoo/odoo/commit/847889b49768db290f86ab5c5f48e8134fa29266) (TODO remove on v14)
#. Some fixes so that you can change to a journal of different company and everthing is updated correctly

TODO (Viejo):
arreglar para los statments, por ahora no pudismo hacer que nade bien, sobre todo la parte de que
cuentas ofrece para seleccionar. Tal vez podemos ver de dejar eso de esa manera.
Al respecto de como se genera esto esta este codigo:
<table class="o_group o_inner_group o_group_col_6 create_group_right"><!-- here come some form_create_field --></table>

A su vez hay que cambiar self.env.company por self.journal_id.company_id en "account.bank.statement", tal vez un pr a odoo?

Installation
============

To install this module, you need to:

#. Only need to install the module.

Configuration
=============

To configure this module, you need to:

#. Nothing to configure.

Usage
=====

To use this module, you need to:

#. Just Use it!

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

Images
------

* |company| |icon|

Contributors
------------

Maintainer
----------

|company_logo|

This module is maintained by the |company|.

To contribute to this module, please visit https://www.adhoc.com.ar.

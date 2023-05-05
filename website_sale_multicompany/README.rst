.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

==============================
Website Sale Multicompany
==============================

# Con este modulo, cuando un usuario hace una compra en sitio web la misma se hará en la compañía por defecto que tenga seteada el usuario (company_id) en vez de la compañía del sitio web. Los métodos de envío y pago que se mostrarán serán lo de la compañía de la orden.

Installation
============

To install this module, you need to:

#. Only install the module

Configuration
=============

To configure this module, you need to:

#. Go to a Payment acquirer and select a journal that belongs to a different company than the Payment method

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

Usage
=====

.. image:: https://odoo-community.org/website/image/ir.attachment/5784_f2813bd/datas
   :alt: Try me on Runbot
   :target: http://runbot.adhoc.com.ar/


* |company| |icon|
* Eficent |iconEficent| Part of the code used for this module was extracted from Eficent's `multicompany-fixes/mcfix_accpount <https://github.com/Eficent/multicompany-fixes/tree/11.0/mcfix_account>`_ module

Contributors
------------

Maintainer
----------

|company_logo|

This module is maintained by the |company|.

To contribute to this module, please visit https://www.adhoc.com.ar.

Este modulo es para que usuarios portal vean registros de las compañías que tienen asignadas como compañías permitidas (company_ids). Por defecto Odoo suele dejar ver solo lo de la compañía del sitio web.

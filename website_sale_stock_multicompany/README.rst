.. |company| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

===================================
Website Sale Stock Multicompany
===================================

This module extends the functionality of website_sale_stock and website_sale_multicompany to properly handle warehouse assignments in multi-company environments when selling through the website.

Installation
============

To install this module, you need to:

#. Just install the module.
#. This module is auto-installable when both website_sale_stock and website_sale_multicompany are installed.

Configuration
=============

No additional configuration is needed.

Usage
=====

This module works automatically in the background. It ensures that:

* When a sale order is created through the website, the correct warehouse is assigned based on the user's company.
* If the assigned warehouse doesn't belong to the user's company, it automatically searches for an appropriate warehouse that does.
* The warehouse selection respects multi-company rules and defaults.

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

* ADHOC SA: `Icon <http://fotos.subefotos.com/83eab0381f1e15a8de24b1b91b2896a2o.png>`_.

Contributors
------------

Maintainer
----------

.. image:: http://fotos.subefotos.com/83eab0381f1e15a8de24b1b91b2896a2o.png
   :alt: Odoo Community Association
   :target: https://www.adhoc.com.ar

This module is maintained by the ADHOC SA.

To contribute to this module, please visit https://www.adhoc.com.ar.

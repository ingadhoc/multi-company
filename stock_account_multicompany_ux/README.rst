.. |company| replace:: ADHOC SA

.. |company_logo| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-logo.png
   :alt: ADHOC SA
   :target: https://www.adhoc.com.ar

.. |icon| image:: https://raw.githubusercontent.com/ingadhoc/maintainer-tools/master/resources/adhoc-icon.png

.. image:: https://img.shields.io/badge/license-AGPL--3-blue.png
   :target: https://www.gnu.org/licenses/agpl
   :alt: License: AGPL-3

====================================
Stock Account Multicompany Usability
====================================

Extends the stock-accounting integration for multi-company setups where a parent
company has one or more branch companies. The key feature is **Shared Stock
Valuation to Branches**: branches calculate COGS using the parent company's
inventory cost instead of their own, ensuring a single unified cost across
the entire group.

Features
--------

- **Shared Stock Valuation to Branches** (``product.category``): new boolean
  field on product categories. When enabled on the parent company, the parent's
  costing method and standard price are automatically propagated to all
  accessible branches. The field is hidden for branch users.

- **Branch-aware COGS price** (``stock.move``): overrides
  ``_get_cogs_price_unit()`` so that when a branch generates COGS entries for
  a category with shared valuation, the cost is taken from the parent company.
  Supports standard, average, and FIFO cost methods. For FIFO it looks up
  equivalent parent-company stock moves; when none exist it falls back to the
  parent's last stock valuation layer or standard price.

- **Branch-aware COGS value** (``account.move.line``): overrides
  ``_get_cogs_value()`` to apply the same parent-cost logic even when there are
  no associated stock moves (e.g. service products billed from a branch, or
  credit notes). Also respects reversed-entry lines to avoid re-computing
  already-posted COGS.

- **Inventory difference lines** (``account.move``): overrides
  ``_stock_account_prepare_realtime_out_lines_vals()`` to post the price
  difference between the branch cost and the parent cost to the appropriate
  inventory difference account when real-time valuation is active.

- **Branch-aware "Manage Multiple Warehouses" permission** (``stock.warehouse``):
  overrides ``_check_multiwarehouse_group()`` so the warehouse count is grouped
  by the **root company** (``company_id.root_id``) instead of by each individual
  company. This way warehouses belonging to a parent company and its branches are
  summed together, and the ``stock.group_stock_multi_warehouses`` permission is
  auto-enabled/disabled based on the whole group. Companies without branches keep
  the standard behaviour (``root_id`` is the company itself).

Installation
============

To install this module, you need to:

#. Install ``account_multicompany_ux`` and ``stock_account`` (declared as
   dependencies; they are installed automatically).
#. Install this module.

Configuration
=============

#. On the **parent** company, open **Inventory → Configuration → Product
   Categories** and edit the category you want to share.
#. In the *Account Properties* tab, enable **Shared Stock Valuation to
   Branches**.
#. Save. The module will immediately propagate the costing method and valuation
   type to all branches that the current user can access.

.. note::
   The **Shared Stock Valuation to Branches** field is only visible when
   multi-company mode is active and the current company is *not* a branch
   (i.e. it has no parent company).

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/ingadhoc/multi-company/issues>`_.

Credits
=======

Authors
~~~~~~~

* |company|

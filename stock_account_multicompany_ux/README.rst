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

Extends the stock integration for multi-company setups where a parent company has
one or more branch companies. Two independent features: **Shared Stock Valuation
to Branches**, where branches calculate COGS using the parent company's inventory
cost instead of their own to keep a single unified cost across the group; and
**Branch Stock**, which lets a user see where the group's stock is, without
changing the quantity on hand of their own company.

Features
--------

- **Shared Stock Valuation to Branches** (``product.category``): company-dependent
  selection, edited on the parent company and synced to its branches, with three
  options:

  - **Not shared**: the parent and each branch value their stock on their own.
  - **Stock on the parent**: for a parent company that keeps the stock and the
    purchases while its branches only invoice (for example, a branch to invoice in
    B). The parent's costing method, valuation and accounts are propagated to the
    branches, and their invoices take the cost of goods sold at the parent's cost.
    It can only be chosen while no branch has an active warehouse, and a branch
    cannot create or unarchive a warehouse while its parent uses it.
  - **Parent's cost, stock on the branches**: every branch keeps stock in its own
    warehouses, valued at standard cost whatever the parent uses, with its own
    inventory valuation (periodic or perpetual). Each branch takes the parent's cost (copied, with its cost history, on
    every change on the parent), so the branches' purchases do not change it.
    With an average cost on the parent, the average counts the quantities in the
    branches' warehouses too: only the parent's receipts set the cost, and the
    branches' moves add or take units at the current cost. It can only be chosen
    while every branch has an active warehouse; archiving the last warehouse of a
    branch shows a warning.

- **Locked on branches**: while a category is shared, a branch cannot change what
  the parent sets (the costing method; with "Stock on the parent", also the
  valuation, the accounts and the stock journal), nor the cost of its products. To configure
  a branch on its own, set the field to "Not shared" on the parent company.

- **Branch-aware COGS price** (``stock.move``): overrides
  ``_get_cogs_price_unit()`` so that when a branch generates COGS entries for
  a category with shared valuation, the cost is taken from the parent company.
  Supports standard, average, and FIFO cost methods. For FIFO it looks up
  equivalent parent-company stock moves and weights their value by quantity;
  when none exist it falls back to the parent's standard price.

- **Branch-aware COGS value** (``account.move.line``): overrides
  ``_get_cogs_value()`` to apply the same parent-cost logic even when there are
  no associated stock moves (e.g. service products billed from a branch, or
  credit notes). With no stock moves, standard/average take the parent's
  standard price and FIFO is valued with ``product._run_fifo()`` in the parent
  company, same as standard Odoo. Also respects reversed-entry lines to avoid
  re-computing already-posted COGS.

- **Inventory difference lines** (``account.move``): overrides
  ``_stock_account_prepare_realtime_out_lines_vals()`` to post the price
  difference between the branch cost and the parent cost to the appropriate
  inventory difference account when real-time valuation is active.

- **Accounting value per company** (``res.company.stock_accounting_value``): the
  parent adds the branches' valuation entries only for "Stock on the parent"
  categories, and a branch leaves those out. With the other options each company
  books its own stock.

- **Branch Stock** (``stock.location``, ``stock.quant`` record rules): new privilege
  that lets a user read the locations and quants of the whole parent/branches scheme,
  so the stock detail breakdowns list every warehouse of the group even for companies
  the user cannot access. The **quantity on hand stays unchanged** — it keeps showing
  only the user's own companies, because it is scoped by the active companies and not
  by the record rules. The intent is that a salesperson sells from their own branch
  first and only checks the rest of the group when their own stock is not enough.

  Only **read** access is widened. Odoo's company rules on those two models keep
  governing write, create and unlink with their original strict domain, so the user
  cannot touch the other companies' records. Their read permission is turned off so
  that the rules above are the ones that apply, and ``uninstall_hook`` restores it.

Installation
============

To install this module, you need to:

#. Install ``account_multicompany_ux`` and ``stock_account`` (declared as
   dependencies; they are installed automatically).
#. Install this module.

.. note::
   The stock detail breakdowns themselves come from ``product_stock_by_location``
   (product list and kanban) and ``sale_stock_ux`` (sale order line). They are not
   dependencies: without them the privilege simply has nothing to widen.

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

To grant the **Branch Stock** privilege:

#. Open **Settings → Users & Companies → Users** and edit the user.
#. In the *Access Rights* tab, under **Supply Chain**, set **Branch Stock** to
   *All Branches*. The default, *Own company only*, keeps Odoo's native
   behaviour.

Bug Tracker
===========

Bugs are tracked on `GitHub Issues <https://github.com/ingadhoc/multi-company/issues>`_.

Credits
=======

Authors
~~~~~~~

* |company|

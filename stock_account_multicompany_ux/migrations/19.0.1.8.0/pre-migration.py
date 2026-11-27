import json
import logging

_logger = logging.getLogger(__name__)


def migrate(cr, version):
    """shared_to_branches goes from a boolean to a selection, both company-dependent (jsonb).

    An enabled flag becomes 'parent_stock' only for a group whose branches have no
    active warehouse (stock on the parent, branches that only invoice). In any other
    group it is left as 'none', and logged: the customer chooses whether 'parent_cost'
    fits.
    """
    cr.execute(
        """
        SELECT data_type FROM information_schema.columns
         WHERE table_name = 'product_category' AND column_name = 'shared_to_branches'
        """
    )
    row = cr.fetchone()
    if not row or row[0] != "jsonb":
        return

    cr.execute(
        """
        SELECT DISTINCT split_part(c.parent_path, '/', 1)::int
          FROM stock_warehouse w
          JOIN res_company c ON c.id = w.company_id
         WHERE w.active AND c.parent_id IS NOT NULL
        """
    )
    roots_with_branch_warehouses = {root_id for (root_id,) in cr.fetchall()}
    cr.execute("SELECT id, split_part(parent_path, '/', 1)::int FROM res_company")
    root_by_company = dict(cr.fetchall())

    cr.execute("SELECT id, shared_to_branches FROM product_category WHERE shared_to_branches IS NOT NULL")
    skipped = {}
    for categ_id, values in cr.fetchall():
        new_values = {}
        for company_id, enabled in values.items():
            if enabled is not True:
                continue
            root_id = root_by_company.get(int(company_id))
            if root_id in roots_with_branch_warehouses:
                skipped.setdefault(root_id, set()).add(categ_id)
                continue
            new_values[company_id] = "parent_stock"
        cr.execute(
            "UPDATE product_category SET shared_to_branches = %s WHERE id = %s",
            [json.dumps(new_values) if new_values else None, categ_id],
        )
    for root_id, categ_ids in skipped.items():
        _logger.info(
            "Shared stock valuation left as 'Not shared' on company %s: its branches have active "
            "warehouses. Categories: %s",
            root_id,
            sorted(categ_ids),
        )
